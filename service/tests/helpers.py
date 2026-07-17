"""
Helper classes for unit tests.

I know...kitchen sinks are nasty....but they exist for a good reason.
"""

from functools import wraps
from typing import Callable


class SortedList[T](list):
    """list subclass that sorts on insert"""

    key: Callable[[T], int] | None = None

    def __init__(self, *args, key=None):
        super().__init__(*args)
        self.key = key

    @staticmethod
    def _sort(func):
        """decorator to sort the list after calling wrapped function"""

        @wraps(func)
        def _wrap(self, *args, **kwargs):
            try:
                func(self, *args, **kwargs)
            finally:
                self.sort(key=self.key)

        return _wrap

    __add__ = _sort(list.__add__)
    __delitem__ = _sort(list.__delitem__)
    __iadd__ = _sort(list.__iadd__)
    __imul__ = _sort(list.__imul__)
    __setitem__ = _sort(list.__setitem__)
