from unittest import TestCase
from unittest.mock import MagicMock

from sqlalchemy import select
from fixtures import kwargs
from kiln_controller.client import Phase, PhaseType
from kiln_controller.service.models.user import User
from ._fixtures import user_fixture, schedule_fixture
from ._fixtures import mock_service_fixture, client_fixture


class TestPhases(TestCase):
    """Test phases"""

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture()
    def test_phase_order(self, mock_service, schedule, **kwargs):
        """
        Test that phases are ordered by ordinal rather than insert order.

        This doesn't really test that the get() orders by ordinal since there
        is a unique constraint on (schedule_id, ordinal). The index for this
        constraint is the only one for schedule, so the natural order of phases
        by schedule includes ordinal. I have manually verified that changing
        the order_by for that query to Phase.ordinal.desc() changes correctly
        changes the order and causes this test to fail.
        """

        phase2 = Phase("phase2", 2, PhaseType.RAMP, temperature=950)
        phase1 = Phase("phase1", 1, PhaseType.RAMP, temperature=1000)

        with mock_service.patch():
            schedule.phases += phase2
            schedule.phases += phase1

            self.assertEqual([phase1, phase2], schedule.phases)
