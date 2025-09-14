# pylint: disable=missing-class-docstring
# pylint: disable=missing-function-docstring
# pylint: disable=too-few-public-methods
"""
Test the kiln_controller python client library.
"""

from contextlib import contextmanager
from functools import wraps
import random
from typing import Tuple, Callable, Any
import unittest

import pytest
from skytap.fixtures import fixture, default_fixture_name, pass_self

from kiln_controller.client import Client, User, Device, Schedule, Phase
from kiln_controller.client.client import Resource
from kiln_controller.client.mock_service import MockService, Call


class ClientTest(unittest.TestCase):
    """
    Test the kiln_controller Client

    This test supports a LIVE_SERVICE=true environment variable to allow the
    tests to be executed against a live service rather than mocks.
    """

    # maxDiff = None  # I really do want to see the error

    @default_fixture_name('mock_service')
    @pass_self
    def _mock_service(self, **_):
        return MockService()

    @default_fixture_name('client')
    @pass_self
    def _client(self, mock_service, **_):
        with mock_service.patch():
            return Client()

    @fixture(_mock_service)
    def test_client_init(self, mock_service):
        with mock_service.patch():
            client = Client()
        self.assertIsNotNone(client)

    @fixture(_mock_service)
    def _test_list_add(self, _type_list_getter, *args, iadd=False,
                       mock_service):
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
            client = Client()

            _list = list_getter(client)

            # add it to the list
            if iadd:
                _list += obj
            else:
                _list.append(obj)

        # make sure the obj exists
        self.assertTrue(obj in _list, f"{obj} not in {_list}")

        # get a new client, make sure it exists there as well
        with mock_service.patch():
            client = Client()
            _list = list_getter(client)
        self.assertTrue(obj in _list)

    def test_append_user_to_list(self):
        return self._test_list_add((User, lambda client: client.users), \
                                   # pylint: disable=missing-kwoa
                                   "name")

    def test_add_user_to_list(self):
        return self._test_list_add((User, lambda client: client.users), \
                                   # pylint: disable=missing-kwoa
                                   "name", iadd=True)

    def test_add_device_to_list(self):
        return self._test_list_add((Device, lambda client: client.devices), \
                                   # pylint: disable=missing-kwoa
                                   "name", "host", 5000, 'description',
                                   iadd=True)

    def test_append_device_to_list(self):
        return self._test_list_add((Device, lambda client: client.devices), \
                                   # pylint: disable=missing-kwoa
                                   "name", "host", 5000, 'description')

    def test_add_schedule_to_list(self):
        return self._test_list_add((Schedule, \
                                   # pylint: disable=missing-kwoa
                                    lambda client: client.schedules),
                                   "name", iadd=True)

    def test_append_schedule_to_list(self):
        return self._test_list_add((Schedule, \
                                   # pylint: disable=missing-kwoa
                                    lambda client: client.schedules),
                                   "name")

    @fixture(_mock_service)
    def _test_post(self, resource, mock_service):
        """
        test that resources of type _type can be created using
        Resource.post(client)
        """
        self.assertIsNone(resource.id)  # precondition check

        with mock_service.patch():
            client = Client()

            # test post success
            resource.post(client)
            self.assertIsNotNone(resource.id,
                                 "post failed to assign id to resource")

            # test post with resource.id fails
            self.assertRaises(AttributeError, resource.post, client)

    def test_post_user(self):
        return self._test_post(User("name")) \
            # pylint: disable=no-value-for-parameter,not-callable

    def test_post_device(self):
        return self._test_post(Device("name", "host", 5000)) \
            # pylint: disable=no-value-for-parameter,not-callable

    def test_post_schedule(self):
        return self._test_post(Schedule("name")) \
            # pylint: disable=no-value-for-parameter,not-callable

    @fixture(_mock_service)
    def _test_put(self, resource, mock_service):
        """
        test that resources of type _type can be created and updated using
        Resource.put(client)
        """
        with mock_service.patch():
            client = Client()

            # test put create success
            # good chance this won't collide...right?
            resource.id = int(random.random() * 1000000)
            resource.put(client)
            self.assertIsNotNone(resource.id,
                                 "put failed to assign id to resource")

            # test put with resource.id succeeds, attribute changes
            name = f"{resource.name}{resource.name}"
            resource.name = name
            resource.put(client)

            # Verify name is updated by creating a new bare Resource with only
            # id and getting it with the client.
            resource2 = type(resource).__new__(type(resource))
            resource2.id = resource.id
            resource2.get(client)

            self.assertEqual(name, resource2.name, "name not updated in put")

    def test_put_user(self):
        return self._test_put(User("name")) \
            # pylint: disable=no-value-for-parameter,not-callable

    def test_put_device(self):
        return self._test_put(Device("name", "host", 5000)) \
            # pylint: disable=no-value-for-parameter,not-callable

    def test_put_schedule(self):
        return self._test_put(Schedule("name")) \
            # pylint: disable=no-value-for-parameter,not-callable

    @contextmanager
    def _mock_client_requests(self):
        """context manager that replaces client.requests with a mock"""
        mock = None
        try:
            yield mock
        finally:
            pass

    @pass_self
    def _resource(self, _type, *args, client, mock_service,
                  parent: Callable[[...], Resource] = lambda *_, **__: None,
                  include_kwargs: Tuple[str] | None = None, **kwargs):
        """
        create a resource of the given _type using client.
        - parent - callable that produces the parent resource, typically by
                   extracting it from kwargs.
        - include_kwargs - if not None the list of kwargs to pass to resource
        """
        parent = parent(*args, **kwargs)
        kwargs = {k: v for k, v in kwargs.items()
                  if include_kwargs is None or k in include_kwargs}
        resource = _type(*args, parent=parent, **kwargs)
        with mock_service.patch():
            resource.post(client)
        return resource

    def _test_delete_resource(self, resource, mock_service):
        """test that Resource.delete() functions"""
        self.assertIsNotNone(resource.id)

        resource.delete()

        self.assertEqual([Call(mock_service.delete.__name__,
                               (resource.full_url,),
                               {'timeout': 5},
                               return_={})],
                         mock_service.calls)
        self.assertIsNone(resource.id)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, User, "name", fixture_name='user')
    def test_delete_user_resource(self, client, user, mock_service):
        del client
        with mock_service.patch():
            return self._test_delete_resource(user, mock_service=mock_service)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Device, "name", "host", 5000, fixture_name='device')
    def test_delete_device_resource(self, client, device, mock_service):
        del client
        with mock_service.patch():
            return self._test_delete_resource(device, mock_service=mock_service)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def test_delete_schedule_resource(self, client, schedule, mock_service):
        del client
        with mock_service.patch():
            return self._test_delete_resource(schedule,
                                              mock_service=mock_service)

    def _test_delete_resource_by_list(self, resource_list, resource,
                                      mock_service):
        """test that Resource.delete() functions"""

        with mock_service.patch():
            resource_list.refresh()  # ensure the view is in sync with resource

            self.assertTrue(resource in resource_list)

        with mock_service.patch():
            idx = resource_list.index(resource)
            del resource_list[idx]

        # Delete is followed by get to refresh the updated list.
        # Don't validate the get call to avoid existing resources causing
        # failures when live_service=true.
        self.assertEqual(['delete', 'get'],
                         [call.method for call in mock_service.calls])
        self.assertEqual(Call(mock_service.delete.__name__,
                              (resource.full_url,),
                              {'timeout': 5},
                              return_={}),
                         mock_service.calls[0])
        self.assertFalse(resource in resource_list)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, User, "name", fixture_name='user')
    def test_delete_user_resource_by_list(self, client, user, mock_service):
        return self._test_delete_resource_by_list(client.users, user,
                                                  mock_service=mock_service)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Device, "name", "host", 5000, fixture_name='device')
    def test_delete_device_resource_by_list(self, client, device,
                                            mock_service):
        return self._test_delete_resource_by_list(client.devices, device,
                                                  mock_service=mock_service)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def test_delete_schedule_resource_by_list(self, client, schedule,
                                              mock_service):
        return self._test_delete_resource_by_list(client.schedules, schedule,
                                                  mock_service=mock_service)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def test_basic_schedule_phases_resource_list(self, client, schedule,
                                                 mock_service):
        '''basic test that schedule.phases ResourceList works'''
        self.assertEqual([], schedule.phases)

        phase = Phase('name', 'type', None, 5)
        self.assertIsNone(phase._url)
        with mock_service.patch():
            schedule.phases += phase
        self.assertEqual([phase], schedule.phases)
        self.assertEqual(f"{schedule._url}/phase/{phase.id}", phase._url)
        self.assertEqual(f"{schedule._url}/phase/{phase.id}",
                         schedule.phases[0]._url,
                         'resource list element has url')

        with mock_service.patch():
            del schedule.phases[0]
        self.assertEqual([], schedule.phases)

    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    @fixture(_resource, Phase,
             "name",  # name
             "type",  # type
             0,       # duration
             0,      # rate
             parent=lambda *args, **kwargs: kwargs.get('schedule'),
             fixture_name='phase', include_kwargs=())
    def test_schedule_delete_deletes_phases(self, client, schedule, phase,
                                                 mock_service):
        '''basic test that deleting a schedule deletes its phases'''
        with mock_service.patch():
            schedule.delete()

            with self.assertRaises(NotImplemented):  # todo use proper exception
                phase.refresh()


if __name__ == '__main__':
    pytest.main()
