"""
helpers for the client
Contains things like logging, trace decorators, etc.
"""

from collections.abc import Callable
from functools import wraps
import logging
from typing import Any, Concatenate, Protocol

logger = logging.getLogger("kiln_controller.client")
trace_logger = logging.getLogger("kiln_controller.client")


class _Response(Protocol):
    status_code: int
    text: str


def trace[**P, R: _Response](
    func: Callable[P, R],
    /,
    *,
    log_func: Callable[..., Any] = trace_logger.error,
) -> Callable[P, R]:
    """
    decorator to trace method call, return, raise
    Can be applied directly to the function or accept these kw_only arguments:
      log_func - the log function to use (default: trace_logger.debug)
    """

    @wraps(func)
    def trace_(*args: P.args, **kwargs: P.kwargs) -> R:
        log_func("%s(%s, %s)", func.__name__, args, kwargs)
        try:
            ret = func(*args, **kwargs)
            log_func(
                "%s(%s, %s) = %s",
                func.__name__,
                args,
                kwargs,
                f"{ret.status_code} {ret.text}" if hasattr(ret, "text") else ret,
            )
            return ret
        except Exception as e:
            log_func("%s(%s, %s) raised %s", func.__name__, args, kwargs, e)
            raise e

    if func is not None:
        return trace_

    def _wrap(_func: Callable[P, R]) -> Callable[P, R]:
        nonlocal func
        func = _func
        return trace_

    return _wrap


def validate_url(url: str) -> str:
    if not isinstance(url, str):
        raise TypeError("url must be a str")

    if not url:
        raise ValueError(f"url must have a value: {url}")

    if url[0] != "/":
        raise ValueError(f"url must begin with '/':{url}")

    if "/None" in url:
        raise ValueError("url appears to contain an unset " f"'id' attribute: {url}")

    bad_characters = "{}"
    if any(bad in url for bad in bad_characters):
        raise ValueError(f"url contains one of '{bad_characters}': {url}")

    return url


type _UrlCallable[SelfT, **P, R] = Callable[Concatenate[SelfT, str, P], R]


def detect_bad_url[SelfT, **P, R](
    func: _UrlCallable[SelfT, P, R],
) -> _UrlCallable[SelfT, P, R]:
    """
    Decorator that raises a TypeError or ValueError when the url argument is
    invalid.
    This is intended to prevent the client from making bad requests
    to clarify where the error originates from and keep it from
    reaching the server.
    """

    @wraps(func)
    def bad_url_filter(
        self: SelfT, url: str, /, *args: P.args, **kwargs: P.kwargs
    ) -> R:
        validate_url(url)
        return func(self, url, *args, **kwargs)

    return bad_url_filter
