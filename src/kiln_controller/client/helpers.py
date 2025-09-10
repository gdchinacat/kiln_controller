"""
helpers for the client
Contains things like logging, trace decorators, etc.
"""
from functools import wraps
import logging


logger = logging.getLogger("kiln_controller.client")
trace_logger = logging.getLogger("kiln_controller.client")


def noop(*_, **__):
    '''function that accepts all args, kwargs and does nothing'''


def trace(func=None, /, *, log_func=trace_logger.debug):
    """
    decorator to trace method call, return, raise
    Can be applied directly to the function or accept these kw_only arguments:
      log_func - the log function to use (default: trace_logger.debug)
    """
    @wraps(func)
    def wrap(*args, **kwargs):
        log_func("%s(%s, %s)", func.__name__, args, kwargs)
        try:
            ret = func(*args, **kwargs)
            log_func("%s(%s, %s) = %s", func.__name__, args, kwargs, ret)
            return ret
        except Exception as e:
            log_func("%s(%s, %s) raised %s", func.__name__, args, kwargs, e)
            raise e

    if func is not None:
        return wrap

    def _wrap(_func):
        nonlocal func
        func = _func
        return wrap
    return _wrap


def validate_url(url):
    if not isinstance(url, str):
        raise TypeError("url must be a str")

    if not url:
        raise ValueError(f"url must have a value: {url}")

    if url[0] != '/':
        raise ValueError(f"url must begin with '/':{url}")

    if '/None' in url:
        raise ValueError("url appears to contain an unset "
                         f"'id' attribute: {url}")

    bad_characters = '{}'
    if any(bad in url for bad in bad_characters):
        raise ValueError(f"url contains one of '{bad_characters}': {url}")

    return url


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
    def bad_url_filter(self, url, *args, **kwargs):
        validate_url(url)
        return func(self, url, *args, **kwargs)
    return bad_url_filter
