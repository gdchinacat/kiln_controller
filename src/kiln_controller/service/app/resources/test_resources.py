
from unittest import TestCase
from unittest.mock import MagicMock
from .base import BaseResource


class _ResourceType:
    ...


class _Resource(BaseResource):
    TYPE = _ResourceType


class TestResources(TestCase):
    """Test the application resources."""

    def testBaseResourceLookup(self):
        resource = _Resource()
        db = MagicMock()
        _id = 0
        resource._lookup(db, _id)

        query = db.select(_ResourceType).filter_by(id=_id)
        db.session.execute.assert_has_calls(query)
