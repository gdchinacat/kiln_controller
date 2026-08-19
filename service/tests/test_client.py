"""
Test the kiln_controller python client library.
"""

# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
# pylint: disable=unused-argument
# pylint: disable=too-many-public-methods

from contextlib import contextmanager
import random
from typing import Any
import unittest

import pytest

from fixtures import kwargs
from kiln_controller.client import (
    Client,
    User,
    Device,
    Schedule,
    Phase,
    NotFoundException,
)
from kiln_controller.client.client import DEFAULT_TIMEOUT
from kiln_controller.common.enums import PhaseType

from ._fixtures import (
    mock_service_fixture,
    client_fixture,
    device_fixture,
    user_fixture,
    schedule_fixture,
    phase_fixture,
)
from .mock_service import Call

# throwaway ids to make arg lists readable
# todo - get rid of USER_ID, use actual resources
USER_ID = 1


class ClientTest(unittest.TestCase):
    """
    Test the kiln_controller Client

    This test supports a LIVE_SERVICE=true environment variable to allow the
    tests to be executed against a live service rather than mocks.
    """

    # maxDiff = None  # I really do want to see the error

    @ kwargs["mock_service"] << mock_service_fixture()
    def test_client_init(self, mock_service):
        with mock_service.patch():
            client = Client()
        self.assertIsNotNone(client)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    def _test_list_add(
        self, _type_list_getter, *args, iadd=False, mock_service, client
    ):
        """
        helper to add an object.
        _type_list_getter: (_type, list_getter)

        list_getter: func(client) -> ResourceList
        iadd: bool: use += as opposed to .append?
        """

        # unpack the arg telling us what to add and where to add it
        _type, list_getter = _type_list_getter

        # create the resource
        obj = _type(*args)

        with mock_service.patch():
            _list = list_getter(client)

            # add it to the list
            if iadd:
                _list += obj
            else:
                _list.append(obj)

            # make sure the obj exists in the resource list
            self.assertTrue(obj in _list, f"{obj} not in {_list}")

        # get a new client, make sure it exists there as well
        with mock_service.patch():
            client = Client()
            _list = list_getter(client)

            self.assertTrue(obj in _list)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["user"] << user_fixture(skip_create=True, skip_cleanup=True)
    def test_append_user_to_list(self, user, **_):
        return self._test_list_add(
            (User, lambda client: client.users),  # pylint: disable=missing-kwoa
            user.name,
            user.username,
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["user"] << user_fixture(skip_create=True, skip_cleanup=True)
    def test_add_user_to_list(self, user, **_):
        return self._test_list_add(
            (User, lambda client: client.users),  # pylint: disable=missing-kwoa
            user.name,
            user.username,
            iadd=True,
        )

    def test_add_device_to_list(self):
        return self._test_list_add(
            (Device, lambda client: client.devices),  # pylint: disable=missing-kwoa
            "name",
            USER_ID,
            "host",
            5000,
            "description",
            iadd=True,
        )

    def test_append_device_to_list(self):
        return self._test_list_add(
            (Device, lambda client: client.devices),  # pylint: disable=missing-kwoa
            "name",
            USER_ID,
            "host",
            5000,
            "description",
        )

    def test_add_schedule_to_list(self):
        return self._test_list_add(
            (Schedule, lambda client: client.schedules),  # pylint: disable=missing-kwoa
            "name",
            1,
            iadd=True,
        )

    def test_append_schedule_to_list(self):
        return self._test_list_add(
            (Schedule, lambda client: client.schedules),  # pylint: disable=missing-kwoa
            "name",
            1,
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    def _test_post(self, resource, mock_service, client):
        """
        test that resources of type _type can be created using
        Resource.post(client)
        """
        self.assertIsNone(resource.id)  # precondition check

        with mock_service.patch():
            # test post success
            resource.post(client)

            self.assertIsNotNone(resource.id, "post failed to assign id to resource")

            # test post with resource.id fails
            self.assertRaises(AttributeError, resource.post, client)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["user"] << user_fixture(skip_create=True)
    def test_post_user(self, user, **_):
        return self._test_post(
            user
        )  # pylint: disable=no-value-for-parameter,not-callable

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["device"] << device_fixture(skip_create=True)
    def test_post_device(self, device, **kwargs):
        return self._test_post(
            device
        )  # pylint: disable=no-value-for-parameter,not-callable

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture(skip_create=True)
    def test_post_schedule(self, user, schedule, **_):
        # todo how did this ever work? schedule should require a user!!!
        return self._test_post(
            schedule
        )  # pylint: disable=no-value-for-parameter,not-callable

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    def _test_put(self, resource, mock_service, client):
        """
        test that resources of type _type can be created and updated using
        Resource.put(client)
        """
        with mock_service.patch():
            # test put create success
            # good chance this won't collide...right?
            resource.id = int(random.random() * 1000000)
            resource.put(client)
            self.assertIsNotNone(resource.id, "put failed to assign id to resource")

            # test put with resource.id succeeds, attribute changes
            name = resource.name * 2
            resource.name = name
            resource.put(client)

            # Verify name is updated by creating a new bare Resource with only
            # id and getting it with the client.
            resource2 = type(resource).__new__(type(resource))
            resource2.id = resource.id
            resource2.get(client)

            self.assertEqual(name, resource2.name, "name not updated in put")

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["user"] << user_fixture(skip_create=True)
    def test_put_user(self, user, **_):
        return self._test_put(
            user
        )  # pylint: disable=no-value-for-parameter,not-callable

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["device"] << device_fixture(skip_create=True)
    def test_put_device(self, device, **_):
        return self._test_put(
            device,
        )  # pylint: disable=no-value-for-parameter,not-callable

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture(skip_create=True)
    def test_put_schedule(self, schedule, **_):
        return self._test_put(
            schedule
        )  # pylint: disable=no-value-for-parameter,not-callable

    @contextmanager
    def _mock_client_requests(self):
        """context manager that replaces client.requests with a mock"""
        mock = None
        try:
            yield mock
        finally:
            pass

    def _test_delete_resource(self, resource, mock_service):
        """test that Resource.delete() functions"""
        self.assertIsNotNone(resource.id)

        resource_url = f"{resource._client._client.url}{resource._url}/"
        resource.delete()

        self.assertEqual(
            [
                Call(
                    mock_service.delete.__name__,
                    (resource_url,),
                    {"timeout": DEFAULT_TIMEOUT},
                    return_={},
                )
            ],
            mock_service.calls,
        )
        self.assertIsNone(resource.id)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture(skip_cleanup=True)
    def test_delete_user_resource(self, client, user, mock_service, **kwargs):
        del client
        with mock_service.patch():
            return self._test_delete_resource(user, mock_service=mock_service)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["device"] << device_fixture(skip_cleanup=True)
    def test_delete_device_resource(self, client, device, mock_service, **kwargs):
        del client
        with mock_service.patch():
            return self._test_delete_resource(device, mock_service=mock_service)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture(skip_cleanup=True)
    def test_delete_schedule_resource(self, client, schedule, mock_service, **kwargs):
        del client
        with mock_service.patch():
            return self._test_delete_resource(schedule, mock_service=mock_service)

    def _test_delete_resource_by_list(self, resource_list, resource, mock_service):
        """test that Resource.delete() functions"""

        with mock_service.patch():
            resource_list.expire()  # ensure the view is in sync with resource

            self.assertTrue(resource in resource_list)

        resource_url = f"{resource._client._client.url}{resource._url}/"
        with mock_service.patch():
            idx = resource_list.index(resource)
            del resource_list[idx]

        self.assertEqual(
            [
                Call(
                    mock_service.delete.__name__,
                    (resource_url,),
                    {"timeout": DEFAULT_TIMEOUT},
                    return_={},
                )
            ],
            mock_service.calls,
        )

        with mock_service.patch():
            self.assertFalse(resource in resource_list)

        self.assertEqual(
            [
                Call(
                    mock_service.get.__name__,
                    (f"{resource._client._client.url}{resource._URL}/",),
                    {"timeout": DEFAULT_TIMEOUT},
                    return_=Any,
                )
            ],
            mock_service.calls,
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    def test_delete_user_resource_by_list(self, client, user, mock_service, **kwargs):
        return self._test_delete_resource_by_list(
            client.users, user, mock_service=mock_service
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["device"] << device_fixture()
    def test_delete_device_resource_by_list(
        self, client, device, mock_service, **kwargs
    ):
        return self._test_delete_resource_by_list(
            client.devices, device, mock_service=mock_service
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture()
    def test_delete_schedule_resource_by_list(
        self, client, schedule, mock_service, **kwargs
    ):
        return self._test_delete_resource_by_list(
            client.schedules, schedule, mock_service=mock_service
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture()
    def test_basic_schedule_phases_resource_list(
        self, schedule, mock_service, **kwargs
    ):
        """basic test that schedule.phases ResourceList works"""
        with mock_service.patch():
            self.assertEqual([], schedule.phases)

        phase = Phase("name", 1, PhaseType.RAMP, None, 5, parent=schedule)
        self.assertEqual(f"{schedule._url}/phase", phase._url)
        with mock_service.patch():
            schedule.phases += phase
            self.assertEqual([phase], schedule.phases)
        self.assertEqual(f"{schedule._url}/phase/{phase.id}", phase._url)
        self.assertEqual(
            f"{schedule._url}/phase/{phase.id}",
            schedule.phases[0]._url,
            "resource list element has url",
        )

        with mock_service.patch():
            del schedule.phases[0]
            self.assertEqual([], schedule.phases)

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture()
    @ kwargs["phase"] << phase_fixture()
    def test_schedule_phases_resource_list_clear_get(
        self, schedule, phase, client, mock_service, **kwargs
    ):
        """basic test that schedule.phases ResourceList works"""

        with mock_service.patch():
            # clear the phases to force a reload
            self.assertEqual([], mock_service.calls)
            schedule.phases.clear()
            self.assertEqual([], mock_service.calls)

            # Access the resource list twice, only the first should generate a
            # call.
            phases = [phase for phase in schedule.phases]
            _ = [phase for phase in schedule.phases]

        self.assertEqual([phase], phases)

        self.assertEqual(
            [
                Call(
                    mock_service.get.__name__,
                    (f"{client._client.url}{schedule._url}/phase/",),
                    {"timeout": DEFAULT_TIMEOUT},
                    return_=[phase.asdict()],
                )
            ],
            mock_service.calls,
        )

    @ kwargs["mock_service"] << mock_service_fixture()
    @ kwargs["client"] << client_fixture()
    @ kwargs["user"] << user_fixture()
    @ kwargs["schedule"] << schedule_fixture(skip_cleanup=True)
    @ kwargs["phase"] << phase_fixture(skip_cleanup=True)
    def test_schedule_delete_deletes_phases(
        self, client, schedule, phase, mock_service, **kwargs
    ):
        """basic test that deleting a schedule deletes its phases"""
        with mock_service.patch():
            schedule.delete()

            with self.assertRaises(NotFoundException):
                phase.get()


if __name__ == "__main__":
    pytest.main()
