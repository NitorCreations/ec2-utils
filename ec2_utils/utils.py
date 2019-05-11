import json
import requests
import sys
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
from retry import retry
from urllib3.util.retry import Retry
from botocore.exceptions import ClientError, EndpointConnectionError

def get_retry(url, retries=5, backoff_factor=0.3,
              status_forcelist=(500, 502, 504), session=None, timeout=5):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session.get(url, timeout=5)

def wait_net_service(server, port, timeout=None):
    """ Wait for network service to appear
        @param timeout: in seconds, if None or 0 wait forever
        @return: True of False, if timeout is None may return only True or
                 throw unhandled network exception
    """
    import socket
    import errno
    s = socket.socket()
    if sys.version < "3":
        # Just make this something that will not be throwns since python 2
        # just has socket.error
        ConnectionRefusedError = EndpointConnectionError
    if timeout:
        from time import time as now
        # time module is needed to calc timeout shared between two exceptions
        end = now() + timeout
    while True:
        try:
            if timeout:
                next_timeout = end - now()
                if next_timeout < 0:
                    return False
                else:
                    s.settimeout(next_timeout)
            s.connect((server, port))
        except socket.timeout as err:
            # this exception occurs only if timeout is set
            if timeout:
                return False
        except ConnectionRefusedError:
            s.close()
            return False
        except socket.error as err:
            # catch timeout exception from underlying network library
            # this one is different from socket.timeout
            if not isinstance(err.args, tuple) or err[0] != errno.ETIMEDOUT or err[0] != errno.ECONNREFUSED:
                raise
            elif err[0] == errno.ECONNREFUSED:
                s.close()
                return False
        else:
            s.close()
            return True

def prune_array(prunable, time_func, group_by_func, ten_minutely=None,
                hourly=None, daily=None, weekly=None, monthly=None, yearly=None,
                dry_run=False): 
    
    objects = sorted([obj for obj in prunable], key=time_func)
    keep = set()
    now = datetime.now(tz.UTC)

    if ten_minutely:
        _select_kept(keep, objects, time_func, group_by_func, _start_of_ten_minutes,
                     now - relativedelta(minutes = ten_minutely * 10), now)
    if hourly:
        _select_kept(keep, objects, time_func, group_by_func, _start_of_hour,
                     now - relativedelta(hours = hourly), now)
    if daily:
        _select_kept(keep, objects, time_func, group_by_func, _start_of_day,
                     now - relativedelta(days = daily), now)
    if weekly:
        _select_kept(keep, objects, time_func, group_by_func, _start_of_week,
                     now - relativedelta(weeks = weekly), now)
    if monthly:
        _select_kept(keep, objects, time_func, group_by_func, _start_of_month,
                     now - relativedelta(months = monthly), now)
    if yearly:
        _select_kept(keep, objects, time_func, group_by_func, _start_of_year,
                     now - relativedelta(years = yearly), now)
    
    delete = sorted(set(objects) - keep, key=time_func)
    return keep, delete
    

def _start_of_ten_minutes(date):
    return date.replace(second=0, microsecond=0) - timedelta(minutes=date.minute % 10)

def _start_of_hour(date):
	return date.replace(minute=0, second=0, microsecond=0)

def _start_of_day(date):
	return date.replace(hour=0, minute=0, second=0, microsecond=0)

def _start_of_week(date):
	return date.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days = date.weekday())

def _start_of_month(date):
	return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

def _start_of_year(date):
	return date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)

def _select_kept(keep, obects, time_func, group_by_func, start_func, end, now):
	groups = {}
	prev = None
	for obj in obects:
		obj_time = time_func(obj)
		obj_group = group_by_func(obj)
		if obj_group not in groups:
		    groups[obj_group] = {"curr": None, "prev": None}
		groups[obj_group]["curr"] = start_func(obj_time)
		if groups[obj_group]["curr"] != groups[obj_group]["prev"] \
		   and (obj_time > end or end > now):
			keep.add(obj)
		groups[obj_group]["prev"] = groups[obj_group]["curr"]
        if obj_time < end:
            return

def delete_selected(full_array, deleted, name_func, time_func, dry_run=False):
    has_deleted = False
    for obj in full_array:
        print(name_func(obj))
        if obj not in deleted:
            print(colored("Skipping " + name_func(obj), "cyan") +
                  " || " + time.strftime("%a, %d %b %Y %H:%M:%S",
                  time_func(obj).timetuple()))
        else:
            print(colored("Deleting " + name_func(obj), "yellow") +
                  " || " + time.strftime("%a, %d %b %Y %H:%M:%S",
                  time_func(obj).timetuple()))
            has_deleted = True
            try:
                if not dry_run:
                    delete_object(obj)
                    time.sleep(0.3)
            except ClientError as err:
                print(colored("Delete failed: " +
                              err.response['Error']['Message'], "red"))
    if not has_deleted:
        print(colored("Nothin to delete", "green"))

@retry(ClientError, tries=5, delay=1, backoff=3)
def delete_object(obj):
    obj.delete()