# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods

from contextlib import contextmanager
import logging
from typing import List, Tuple, Dict
import unittest

from kiln_controller.client.helpers import (
    trace,
    logger as helper_logger,
    detect_bad_url,
)


class Collector:
    """collects details about trace execution"""

    logged: List[Tuple[Tuple, Dict]] = []  # the log messages
    func_called: bool = False

    def log_func(self, *args, **kwargs):
        self.logged.append((args, kwargs))

    def func(self):
        self.func_called = True


class _TestHandler(logging.Handler):
    """A logging Handler to use to test the default trace log_func"""

    # TODO - update this to use pytest log collection functionality
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emitted: List[Tuple[int, str]] = []

    def emit(self, record) -> None:
        self.emitted.append((record.levelno, record.msg % record.args))

    @staticmethod
    @contextmanager
    def temporary_handler(logger, level=None):
        handler = _TestHandler(logging.DEBUG)
        orig_level = logger.level
        logger.setLevel(level if level is not None else logging.DEBUG)

        logger.addHandler(handler)
        try:
            yield handler
        finally:
            logger.setLevel(orig_level)
            logger.removeHandler(handler)


class TraceTest(unittest.TestCase):

    def test_trace_with_log_func(self):
        # test success
        collector = Collector()
        trace(log_func=collector.log_func)(collector.func)()
        self.assertEqual(
            collector.logged,
            [
                (("%s(%s, %s)", "func", (), {}), {}),
                (("%s(%s, %s) = %s", "func", (), {}, None), {}),
            ],
        )

    def test_bare_trace(self):
        # test success
        with _TestHandler.temporary_handler(helper_logger) as handler:
            trace(int)()
        self.assertEqual(
            handler.emitted,
            [
                (logging.DEBUG, "int((), {})"),
                (logging.DEBUG, "int((), {}) = 0"),
            ],
        )

    def test_bare_trace_exception(self):
        TestException = type("TestException", (Exception,), {})
        exc = None
        with _TestHandler.temporary_handler(helper_logger) as handler:

            def raises():
                nonlocal exc
                try:
                    raise TestException()
                except Exception as _exc:
                    exc = _exc
                    raise

            self.assertRaises(TestException, trace(raises))

        self.maxDiff = None  # pylint: disable=invalid-name
        self.assertEqual(
            handler.emitted,
            [
                (logging.DEBUG, "raises((), {})"),
                (logging.DEBUG, f"raises((), {{}}) raised {exc}"),
            ],
        )


class DetectBadUrlTest(unittest.TestCase):
    def test_detect_bad_url(self):
        class Test:
            @detect_bad_url
            def test(self, url):
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
            with self.assertRaises(exc_type, msg=f"bad url not detected: '{bad_url}'"):
                test.test(bad_url)
