"""
Test the kiln_controller user resource behavior.
"""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument

import logging
import os

import pytest
from .fixtures import fixture

from kiln_controller.client import ValidationError, ValidationErrors
from .mock_service import LIVE_SERVICE
from .fixtures import (
    CleanupTestCase,
    mock_service_fixture,
    client_fixture,
    user_fixture,
    schedule_fixture,
    device_fixture,
)

if os.getenv("DEBUG_LOGGING", "false").upper() == "TRUE":
    logging.basicConfig(level=logging.DEBUG, force=True)


class UserTest(CleanupTestCase):
    """
    Test phase resources.
    """

    @pytest.mark.skipif(not LIVE_SERVICE, reason="mocks do not perform validation")
    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(schedule_fixture)
    def test_user_delete_fails_with_schedule(self, user, mock_service, **_):
        """
        Verify an error occurs if a user delete is attempted while the user has
        schedules.
        """
        with mock_service.patch():
            with self.assertRaises(ValidationError) as ve:
                user.delete()

        self.assertEqual(ValidationErrors.USER_HAS_SCHEDULES, ve.exception.error)

    @pytest.mark.skipif(not LIVE_SERVICE, reason="mocks do not perform validation")
    @fixture(mock_service_fixture)
    @fixture(client_fixture)
    @fixture(user_fixture)
    @fixture(device_fixture)
    def test_user_delete_fails_with_devices(self, user, mock_service, **_):
        """
        Verify an error occurs if a user delete is attempted while the user has
        schedules.
        """
        with mock_service.patch():
            with self.assertRaises(ValidationError) as ve:
                user.delete()

        self.assertEqual(ValidationErrors.USER_MANAGES_DEVICES, ve.exception.error)
