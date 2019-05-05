from threading import Event, Lock, Thread
from ec2_utils.instance_info import InstanceInfo, wait_net_service

class IntervalThread(Thread):
    def __init__(self, event, interval, call_function):
        Thread.__init__(self)
        self._stopped = event
        self._interval = interval
        self._call_function = call_function

    def run(self):
        while not self._stopped.wait(self._interval):
            self._call_function()

class LogSender(object):
    def __init__(self, file_name, group=None, stream=None):
        self._lock = Lock()
        self._send_lock = Lock()
        self._logs = boto3.client('logs')
        if group:
            self.group_name = group
        else:
            self.group_name = resolve_stack_name()
        self._messages = deque()
        if stream:
            self.stream_name = stream
        else:
            self.stream_name = resolve_instance_id() + "|" + \
                file_name.replace(':', '_').replace('*', '_')
        try:
            self._logs.create_log_group(logGroupName=self.group_name)
        except BaseException:
            pass
        try:
            self._logs.create_log_stream(logGroupName=self.group_name,
                                         logStreamName=self.stream_name)
        except BaseException:
            pass
        self.token = None
        self.send(str(InstanceInfo()))
        self._do_send()
        self._stop_flag = Event()
        self._thread = IntervalThread(self._stop_flag, 2, self._do_send)
        self._thread.start()

    def send(self, line):
        try:
            self._lock.acquire()
            if isinstance(line, bytes):
                line = line.decode('utf-8', 'replace')
            self._messages.append(line.rstrip())
            if 'CLOUDWATCH_LOG_DEBUG' in os.environ:
                print("Queued message")
        finally:
            self._lock.release()

    def _do_send(self):
        events = []
        try:
            self._lock.acquire()
            if len(self._messages) == 0:
                return
            counter = 0
            while len(self._messages) > 0 and counter < 1048576 and \
                    len(events) < 10000:
                message = self._messages.popleft()
                counter = counter + len(message.encode('utf-8', 'replace')) + 26
                if counter > 1048576:
                    self._messages.appendleft(message)
                elif message:
                    event = {}
                    event['timestamp'] = int(time.time() * 1000)
                    event['message'] = message
                    events.append(event)
        finally:
            self._lock.release()
        if len(events) == 0:
            return
        try:
            self._send_lock.acquire()
            if not self.token:
                stream_desc = self._logs.describe_log_streams(logGroupName=self.group_name,
                                                              logStreamNamePrefix=self.stream_name)
                if 'uploadSequenceToken' in stream_desc['logStreams'][0]:
                    self.token = stream_desc['logStreams'][0]['uploadSequenceToken']
            if self.token:
                log_response = self._logs.put_log_events(logGroupName=self.group_name,
                                                         logStreamName=self.stream_name,
                                                         logEvents=events,
                                                         sequenceToken=self.token)
            else:
                log_response = self._logs.put_log_events(logGroupName=self.group_name,
                                                         logStreamName=self.stream_name,
                                                         logEvents=events)
            if 'CLOUDWATCH_LOG_DEBUG' in os.environ:
                print("Sent " + str(len(events)) + " messages to " + self.stream_name)
            self.token = log_response['nextSequenceToken']
        except ClientError:
            self.token = None
            for event in events:
                self.send(event['message'].encode('utf-8', 'replace'))
        finally:
            self._send_lock.release()


def send_log_to_cloudwatch(file_name, group=None, stream=None):
    log_sender = LogSender(file_name, group=group, stream=stream)
    read_and_follow(file_name, log_sender.send)

def resolve_stack_name():
    info = InstanceInfo()
    stack_name = info.stack_name()
    while not stack_name:
        time.sleep(1)
        info.clear_cache()
        stack_name = info.stack_name()

def resolve_instance_id():
    info = InstanceInfo()
    instance_id = info.instance_id()
    while not instance_id:
        time.sleep(1)
        info.clear_cache()
        instance_id = info.instance_id()
    

def read_and_follow(file_name, line_function, wait=1):
    while not (os.path.isfile(file_name) and os.path.exists(file_name)):
        time.sleep(wait)
    with open(file_name) as file_:
        end_seen = False
        while True:
            curr_position = file_.tell()
            line = file_.readline()
            if not line:
                file_.seek(curr_position)
                end_seen = True
            else:
                line_function(line)
                end_seen = False
            if end_seen:
                time.sleep(wait)
