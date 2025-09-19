# pylint: disable=missing-module-docstring
# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument

from unittest import TestCase
from unittest.mock import MagicMock

from skytap.fixtures.fixtures import (fixture, get_default_fixture_name)

from ..client import Phase
from ..common import PhaseType
from ..service.app.resources.base import BaseResource
from .fixtures import (CleanupTestCase, user_fixture, schedule_fixture)
from .fixtures import mock_service_fixture, client_fixture


class _ResourceType:
    ...


class _Resource(BaseResource):
    TYPE = _ResourceType


class TestResources(TestCase):
    """Test the application resources."""

    def test_base_resource_lookup(self):
        resource = _Resource()
        db = MagicMock()
        _id = 0
        resource._lookup(db, _id)  # pylint: disable=protected-access

        query = db.select(_ResourceType).filter_by(id=_id)
        db.session.execute.assert_has_calls(query)


class TestPhases(CleanupTestCase):
    """Test phases"""

    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(schedule_fixture)
    def test_phase_order(self, mock_service,
                         schedule_kwarg=get_default_fixture_name(
                             schedule_fixture),
                         **kwargs):
        """
        Test that phases are ordered by ordinal rather than insert order.

        This doesn't really test that the get() orders by ordinal since there
        is a unique constraint on (schedule_id, ordinal). The index for this
        constraint is the only one for schedule, so he natural order of phases
        by schedule includes ordinal. I have manually verified that changing
        the order_by for that query to Phase.ordinal.desc() changes correctly
        changes the order and causes this test to fail.
        """
        schedule = kwargs[schedule_kwarg]

        phase2 = Phase('phase2', 2, PhaseType.RAMP, temperature=950)
        phase1 = Phase('phase1', 1, PhaseType.RAMP, temperature=1000)

        with mock_service.patch():
            schedule.phases += phase2
            schedule.phases += phase1

            self.assertEqual([phase1, phase2], schedule.phases)
