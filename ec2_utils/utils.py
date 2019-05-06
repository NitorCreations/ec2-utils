import json
import requests
import sys
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
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
