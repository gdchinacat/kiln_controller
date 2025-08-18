import unittest
import logging
from .helpers import trace, logger, detect_bad_url
from typing import List, Tuple, Dict
from contextlib import contextmanager

class Collector:
    """collects details about trace execution"""
    
    logged: List[Tuple[Tuple, Dict]] = [] # the log messages
    func_called: bool = False
        
    def log_func(self, *args, **kwargs):
        self.logged.append((args, kwargs))
    
    def func(self):
        self.func_called = True

class TestHandler(logging.Handler):
    """A logging Handler to use to test the default trace log_func"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.emitted: List[Tuple[int, str]] = []
        
    def emit(self, log_record, *args, **kwargs):
        self.emitted.append((log_record.levelno,
                             log_record.msg))
        
    @staticmethod
    @contextmanager
    def temporary_handler(logger, level=None):
        handler = TestHandler(logging.DEBUG)
        orig_level = logger.level
        logger.setLevel(logging.DEBUG)
        
        logger.addHandler(handler)
        try:
            yield handler
        finally:
            logger.setLevel(orig_level)
            logger.removeHandler(handler)

class TraceTest(unittest.TestCase):
    
    def testTraceWithLogFunc(self):
        # test success
        collector = Collector()
        trace(log_func=collector.log_func)(collector.func)()
        self.assertEqual(collector.logged,
                         [ (("func((), {})",), {}),
                           (("func((), {}) = None",), {}),
                          ])
        
    def testBareTrace(self):
        # test success
        with TestHandler.temporary_handler(logger) as handler:
            trace(int)()
        self.assertEqual(handler.emitted,
                         [(logging.DEBUG, "int((), {})"),
                          (logging.DEBUG, "int((), {}) = 0"),
                          ])

    def testBareTraceException(self):
        exc = None
        with TestHandler.temporary_handler(logger) as handler:
            def raises():
                nonlocal exc
                try:
                    raise Exception()
                except Exception as _exc:
                    # [2:] is to strip out the two new frames between where
                    # trace takes the traceback and where it is taken here
                    exc = _exc
                    raise exc
            self.assertRaises(Exception, trace(raises))

        self.maxDiff = None
        self.assertEqual(handler.emitted,
                         [(logging.DEBUG, "raises((), {})"),
                          (logging.DEBUG,
                           f"raises((), {{}}) raised {exc}"),
                          ])
        
class DetectBadUrlTest(unittest.TestCase):
    def testDetectBadUrl(self):
        class Test:
            @detect_bad_url
            def test(self, url):
                return url
        
        test = Test()
        for (exc_type, bad_url) in (
                        (TypeError, None),   # must be a string
                        (TypeError, 1),      # must be a string
                        (ValueError, ""),     # must have a value
                        (ValueError, "foo"),  # must start with '/'
                        (ValueError, "/{"),   # can't contain format string
                        (ValueError, "/}"),   # can't contain format string
                        (ValueError, "/.../None/..."), # invalid id
                        ):
            with self.assertRaises(exc_type, msg=f"bad url not detected: '{bad_url}'"):
                test.test(bad_url)
        
if __name__ == "__main__":
    import sys;sys.argv = ['', 'Test.testName']
    unittest.main()