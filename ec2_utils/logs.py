# Copyright 2017-2018 Nitor Creations Oy
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Code used under license:
#
# parse_datetime from https://github.com/jorgebastida/awslogs:
#
# Copyright (c) 2015 Benito Jorge Bastida
# All rights reserved.
#
# Revised BSD License
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#  1. Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#  2. Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#
#  3. Neither the name of the author nor the names of other
#     contributors may be used to endorse or promote products derived
#     from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

import locale
import os
import sys
import time
import re
import queue
from builtins import object, range
from past.utils import old_div
from collections import deque
from datetime import datetime, timedelta
from dateutil import tz
from dateutil.parser import parse
from dateutil.tz import tzutc
from termcolor import colored
from threading import Event, Lock, Thread, BoundedSemaphore
from botocore.compat import total_seconds
from threading import Event, Lock, Thread
from ec2_utils.instance_info import info
from retry import retry
from threadlocal_aws.clients import logs


def millis2iso(millis):
    return fmttime(datetime.utcfromtimestamp(old_div(millis, 1000.0)))


def timestamp(tstamp):
    return (tstamp.replace(tzinfo=None) - datetime(1970, 1, 1, tzinfo=None))\
        .total_seconds() * 1000


def fmttime(tstamp):
    return tstamp.replace(tzinfo=tz.tzlocal()).isoformat()[:23]


def uprint(message):
    if message:
        if sys.version_info[0] > 2:
            sys.stdout.write((message.strip() + os.linesep))
        else:
            sys.stdout.write((message.strip() + os.linesep)
                             .encode(locale.getpreferredencoding()))


def validatestarttime(start_time):
    return int(start_time) * 1000 if start_time else int((time.time() - 60) * 1000)


def parse_datetime(datetime_text):
    """Parse ``datetime_text`` into a ``datetime``."""

    if not datetime_text:
        return None

    ago_regexp = r'(\d+)\s?(m|minute|minutes|h|hour|hours|d|day|days|w|weeks|weeks)(?: ago)?'
    ago_match = re.match(ago_regexp, datetime_text)

    if ago_match:
        amount, unit = ago_match.groups()
        amount = int(amount)
        unit = {'m': 60, 'h': 3600, 'd': 86400, 'w': 604800}[unit[0]]
        date = datetime.utcnow() + timedelta(seconds=unit * amount * -1)
    elif datetime_text == "now":
        date = datetime.utcnow()
    else:
        try:
            date = parse(datetime_text)
        except ValueError:
            if int(datetime_text):
                return int(datetime_text)
            else:
                raise ValueError("Unknown date: %s" % datetime_text)

    if date.tzinfo:
        if date.utcoffset != 0:
            date = date.astimezone(tzutc())
        date = date.replace(tzinfo=None)

    return int(total_seconds(date - datetime(1970, 1, 1)))

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
        self._logs = logs()
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
        self.send(str(info()))
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
            self._put_log_events(events)
        except:
            self.token = None
            for event in events:
                self.send(event['message'].encode('utf-8', 'replace'))
        finally:
            self._send_lock.release()

    @retry(tries=5, delay=1, backoff=2)
    def _put_log_events(self, events):
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
        if log_response and 'nextSequenceToken' in log_response:
            self.token = log_response['nextSequenceToken']
        else:
            self.token = None

def send_log_to_cloudwatch(file_name, group=None, stream=None):
    log_sender = LogSender(file_name, group=group, stream=stream)
    read_and_follow(file_name, log_sender.send)

@retry(tries=10, delay=1, backoff=3)
def resolve_stack_name():
    stack_name = info().stack_name()
    if not stack_name:
        info().clear_cache()
        raise Exception("Failed to resolve stack name")
    return stack_name

@retry(tries=10, delay=1, backoff=3)
def resolve_instance_id():
    instance_id = info().instance_id()
    if not instance_id:
        info().clear_cache()
        raise Exception("Failed to resolve instance id")
    return instance_id

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

class CloudWatchLogsThread(Thread):
    def __init__(self, log_group_name, start_time=None):
        Thread.__init__(self)
        self.setDaemon(True)
        self.log_group_name = log_group_name
        self.start_time = start_time
        self.cwlogs = CloudWatchLogsGroups(log_group_filter=self.log_group_name, start_time=self.start_time)

    def stop(self):
        self.cwlogs._stopped.set()

    def run(self):
        self.cwlogs.get_logs()


class CloudWatchLogsGroups(object):
    def __init__(self, log_filter='', log_group_filter='', start_time=None, end_time=None, sort=False):
        self._logs = logs()
        self.log_filter = log_filter
        self.log_group_filter = log_group_filter
        self.start_time = validatestarttime(parse_datetime(start_time))
        self.end_time = parse_datetime(end_time) * 1000 if end_time else None
        self.sort = sort
        self._stopped = Event()

    def filter_groups(self, log_group_filter, groups):
        filtered = []
        for group in groups:
            if re.search(log_group_filter, group['logGroupName']):
                filtered.append(group['logGroupName'])
        return filtered

    def get_filtered_groups(self, log_group_filter):
        resp = self._logs.describe_log_groups()
        filtered_group_names = []
        filtered_group_names.extend(self.filter_groups(self.log_group_filter, resp['logGroups']))
        while resp.get('nextToken'):
            resp = self._logs.describe_log_groups(nextToken=resp['nextToken'])
            filtered_group_names.extend(self.filter_groups(self.log_group_filter, resp['logGroups']))
        return filtered_group_names

    def get_logs(self):
        groups = self.get_filtered_groups(self.log_group_filter)
        log_threads = []
        work_queue = queue.Queue()
        semaphore = BoundedSemaphore(5)
        output_queue = queue.PriorityQueue()
        work_items = []

        for group_name in groups:
            work_item = {'item': {'logGroupName': group_name,
                                  'interleaved': True,
                                  'startTime': self.start_time,
                                  'filterPattern': self.log_filter if self.log_filter else ""
                                  },
                         'meta': {'initialQueriesDone': Event()}
                         }
            if self.end_time:
                work_item['item']['endTime'] = self.end_time
            work_queue.put(work_item)
            work_items.append(work_item)

        for _ in range(10):
            cwlogs_worker = CloudWatchLogsWorker(work_queue, semaphore, output_queue)
            log_threads.append(cwlogs_worker)
            cwlogs_worker.start()

        speed_limiter = SpeedLimitThread(semaphore)
        speed_limiter.start()
        all_initial_queries_done = False
        tailing = True if not self.end_time else False
        wait_time = None if self.sort else 0.0

        while not self._stopped.isSet():
            try:
                if not all_initial_queries_done:
                    loop_queries_done = True
                    for work_item in work_items:
                        if not work_item['meta']['initialQueriesDone'].wait(wait_time):
                            loop_queries_done = False
                    all_initial_queries_done = loop_queries_done
                elif self.sort:
                    time.sleep(5.0)  # allow time to sort while tailing
                self.print_output_if_any(output_queue)
                if all_initial_queries_done and not tailing:
                    raise KeyboardInterrupt
            except KeyboardInterrupt:
                for thread in log_threads:
                    thread.stop()
                speed_limiter.stop()
                return

    def print_output_if_any(self, output_queue):
        while True:
            try:
                uprint(' '.join(output_queue.get(timeout=1.0)[1]))
            except queue.Empty:
                break


class SpeedLimitThread(Thread):
    def __init__(self, semaphore):
        Thread.__init__(self)
        self.semaphore = semaphore
        self._stopped = Event()
        self.setDaemon(True)

    def tick(self):
        while not self._stopped.wait(1.1):
            try:
                for _ in range(5):
                    self.semaphore.release()
            except ValueError:
                pass
        return

    def stop(self):
        self._stopped.set()

    def run(self):
        self.tick()


class LogWorkerThread(Thread):
    def __init__(self):
        Thread.__init__(self)
        self._stopped = Event()
        self.setDaemon(True)

    def list_logs(self):
        return

    def stop(self):
        self._stopped.set()

    def run(self):
        self.list_logs()


class CloudWatchLogsWorker(LogWorkerThread):
    def __init__(self, work_queue, semaphore, output_queue):
        LogWorkerThread.__init__(self)
        self.work_queue = work_queue
        self.semaphore = semaphore
        self.output_queue = output_queue
        self._logs = logs()

    @retry(tries=5, delay=2, backoff=2)
    def filter_log_events(self, item):
        return self._logs.filter_log_events(**item)

    def list_logs(self):
        do_wait = object()

        def generator():
            work_item = None
            last_timestamp = None
            while True:
                if not work_item:
                    work_item = self.work_queue.get()
                    last_timestamp = None
                self.semaphore.acquire()
                response = self.filter_log_events(work_item['item'])
                for event in response.get('events', []):
                    event['logGroupName'] = work_item['item']['logGroupName']
                    last_timestamp = event.get('timestamp', None)
                    yield event

                if 'nextToken' in response:
                    work_item['item']['nextToken'] = response['nextToken']
                else:
                    if 'nextToken' in work_item['item']:
                        work_item['item'].pop('nextToken')
                    if last_timestamp:
                        work_item['item']['startTime'] = last_timestamp + 1
                    work_item['meta']['initialQueriesDone'].set()
                    self.work_queue.put(work_item)
                    work_item = None
                    yield do_wait

        for event in generator():
            if event is do_wait and not self._stopped.wait(0.0):
                continue
            elif self._stopped.is_set():
                return

            output = []
            output.append(colored(millis2iso(event['timestamp']), 'yellow'))
            output.append(colored(event['logGroupName'], 'green'))
            output.append(colored(event['logStreamName'], 'cyan'))
            output.append(event['message'])
            self.output_queue.put((event['timestamp'], output))  # sort by timestamp (first value in tuple)
