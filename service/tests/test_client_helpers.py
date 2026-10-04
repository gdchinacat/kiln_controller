from contextlib import contextmanager
import logging
from typing import List, Tuple, Dict
import pytest

from kiln_controller.client.helpers import (
    trace,
    logger as helper_logger,
    detect_bad_url,
)


def test_trace_with_log_func(caplog: pytest.LogCaptureFixture) -> None:
    # test success
    caplog.set_level(logging.DEBUG)
    trace(None, log_func=helper_logger.debug)(lambda: None)()

    assert [(record.msg, record.args) for record in caplog.records] == [
        ("%s(%s, %s)", ("<lambda>", (), {})),
        ("%s(%s, %s) = %s", ("<lambda>", (), {}, None)),
    ]


def test_bare_trace(caplog: pytest.LogCaptureFixture) -> None:
    # test test_telemetry_send_successs
    caplog.set_level(logging.DEBUG)
    trace(int, log_func=helper_logger.debug)()
    assert [(record.levelno, record.getMessage()) for record in caplog.records] == [
        (logging.DEBUG, "int((), {})"),
        (logging.DEBUG, "int((), {}) = 0"),
    ]


def test_bare_trace_exception(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    TestException = type("TestException", (Exception,), {})
    exc = TestException()
    with pytest.raises(TestException):

        def _raise() -> None:
            raise exc

        trace(_raise, log_func=helper_logger.debug)()

    assert [(record.levelno, record.getMessage()) for record in caplog.records] == [
        (logging.DEBUG, "_raise((), {})"),
        (logging.DEBUG, f"_raise((), {{}}) raised {exc}"),
    ]


def test_detect_bad_url() -> None:
    class Test:
        @detect_bad_url
        def test(self, url: str) -> str:
            return url

    test = Test()
    for exc_type, bad_url in (
        (TypeError, None),  # must be a string
        (TypeError, 1),  # must be a string
        (ValueError, ""),  # must have a value
        (ValueError, "foo"),  # must start with '/'
        (ValueError, "/{"),  # can't contain format string
        (ValueError, "/}"),  # can't contain format string
        (ValueError, "/.../None/..."),  # invalid id
    ):
        with pytest.raises(exc_type):
            test.test(bad_url)  # type: ignore # test passes bad type
