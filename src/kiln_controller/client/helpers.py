"""
helpers for the client
Contains things like logging, trace decorators, etc.
"""
from functools import wraps
import logging
from functools import partial


def noop(*args): ...

logger = logging.getLogger("kiln_controller.client")
trace_logger = logging.getLogger("kiln_controller.client")

def trace(func=None, /, *, log_func=trace_logger.debug):
    """
    decorator to trace method call, return, raise
    Can be applied directly to the function or accept these kw_only arguments:
      log_func - the log function to use (default: trace_logger.debug)
    """
    @wraps(func)
    def wrap(*args, **kwargs):
        log_func(f"{func.__name__}({args}, {kwargs})")
        try:
            ret = func(*args, **kwargs)
            log_func(f"{func.__name__}({args}, {kwargs}) = {ret}")
            return ret
        except Exception as e:
            log_func(f"{func.__name__}({args}, {kwargs}) raised {e}")
            raise e
        
    if func is not None: #
        return wrap
    else:
        def _wrap(_func):
            nonlocal func
            func = _func
            return wrap
        return _wrap
    
def detect_bad_url(func):
    """
    decorator that raises a ValueError when the url argument
    is 'invalid'.
    This is intended to prevent the client from making bad requests
    to clarify where the error originates from and keep it from
    reaching the server.
    TODO - only apply it when debug is enabled?
    """
    @wraps(func)
    def wrap(self, url, *args, **kwargs):
        if not isinstance(url, str):
            raise TypeError(f"url must be a str")
            
        if not url:
            raise ValueError(f"url must have a value: {url}")
            
        if url[0] != '/':
            raise ValueError(f"url must begin with '/':{url}")
        
        bad_characters = '{}'
        if any(bad in url for bad in bad_characters):
            raise ValueError(f"url contains one of '{bad_characters}': {url}")

        return func(self, url, *args, **kwargs)
    return wrap
        
