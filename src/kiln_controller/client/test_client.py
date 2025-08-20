import unittest
from . import Client, User, Device, Schedule, client
import traceback
import random
from contextlib import contextmanager
from skytap.fixtures import fixture, default_fixture_name, pass_self
from unittest.mock import patch, MagicMock, Mock
from http import HTTPStatus
from kiln_controller.client.mock_service import MockService

@contextmanager
def mock_module_attr(module, attr:str):
    """
    Context manager to replace a module attribute with a mock and restore it
    upon completion.
    
    For example:
    @mock_module_attr(client, 'requests')
    def foo(): ...
    
    Will replace module.requests with a mock
    """
    raise Exception("deprecated: use unittest.mock.patch()")
    orig = getattr(module, attr)
    mock = MagicMock()
    try:
        setattr(module, attr, mock)
        yield mock
    finally:
        setattr(module, orig)

class ClientTest(unittest.TestCase):
    
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
    def testClientInit(self, mock_service):
        with mock_service.patch():
            client = Client()
    
    @fixture(_mock_service)
    def _testListAdd(self, _type_list_getter, *args, iadd=False, mock_service):
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
        
            #add it to the list
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
    
    def testAppendUserToList(self):
        return self._testListAdd((User, lambda client: client.users),
                             "name")
        
    def testAddUserToList(self):
        return self._testListAdd((User, lambda client: client.users),
                             "name", iadd=True)
    
    def testAddDeviceToList(self):
        return self._testListAdd((Device, lambda client: client.devices),
                             "name", "host", 5000, 'description', iadd=True)
        
    def testAppendDeviceToList(self):
        return self._testListAdd((Device, lambda client: client.devices),
                             "name", "host", 5000, 'description')
        
    def testAddScheduleToList(self):
        return self._testListAdd((Schedule, lambda client: client.schedules),
                             "name", iadd=True)
        
    def testAppendScheduleToList(self):
        return self._testListAdd((Schedule, lambda client: client.schedules),
                             "name")

    @fixture(_mock_service)
    def _testPost(self, resource, mock_service):
        """test that resources of type _type can be created using Resource.post(client)"""
        self.assertIsNone(resource.id)  #precondition check
        
        with mock_service.patch():
            client = Client()
        
            # test post success
            resource.post(client)
            self.assertIsNotNone(resource.id, "post failed to assign id to resource")
        
            # test post with resource.id fails
            self.assertRaises(AttributeError, resource.post, client)
    
    def testPostUser(self):
        return self._testPost(User("name"))
        
    def testPostDevice(self):
        return self._testPost(Device("name", "host", 5000))
        
    def testPostSchedule(self):
        return self._testPost(Schedule("name"))
    
    @fixture(_mock_service)
    def _testPut(self, resource, mock_service):
        """
        test that resources of type _type can be created and updated using
        Resource.put(client)
        
        """
        with mock_service.patch():
            client = Client()
        
            # test put create success
            resource.id = int(random.random() * 1000000) # good chance this won't collide...right
            resource.put(client)
            self.assertIsNotNone(resource.id, "put failed to assign id to resource")
        
            # test put with resource.id succeeds, attribute changes
            name = f"{resource.name}{resource.name}"
            resource.name = name
            resource.put(client)
        
            # Verify name is updated by creating a new bare Resource with only id
            # and getting it with the client.
            resource2 = type(resource).__new__(type(resource))
            resource2.id = resource.id
            resource2.get(client)
        
            self.assertEqual(name, resource2.name, "name not updated in put")
        
    def testPutUser(self):
        return self._testPut(User("name"))
        
    def testPutDevice(self):
        return self._testPut(Device("name", "host", 5000))
        
    def testPutSchedule(self):
        return self._testPut(Schedule("name"))
    
    @contextmanager
    def _mock_client_requests(self):
        """context manager that replaces client.requests with a mock"""
        mock = None
        try:
            yield mock
        finally:
            pass
        
    @pass_self
    def _resource(self, _type, *args, client, mock_service, **kwargs):
        """
        create a resource of the given _type using client.
        """
        resource = _type(*args, **kwargs)
        with mock_service.patch():
            resource.post(client)
        return resource
        
    def _testDeleteResource(self, resource):
        """test that Resource.delete() functions"""
        self.assertIsNotNone(resource.id)
        resource.delete()
        # todo - verify requests.delete(...) is called
        self.assertIsNone(resource.id)
    
    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, User, "name", fixture_name='user')
    def testDeleteUserResource(self, client, user, mock_service):
        with mock_service.patch():
            return self._testDeleteResource(user)
    
    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Device, "name", "host", 5000, fixture_name='device')
    def testDeleteDeviceResource(self, client, device, mock_service):
        with mock_service.patch():
            return self._testDeleteResource(device)
    
    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def testDeleteScheduleResource(self, client, schedule, mock_service):
        with mock_service.patch():
            return self._testDeleteResource(schedule)
    
    def _testDeleteResourceByList(self, resource_list, resource, mock_service):
        """test that Resource.delete() functions"""
        
        with mock_service.patch():
            resource_list.refresh() # ensure the view is in sync with resource
        
            self.assertTrue(resource in resource_list)
        
            idx = resource_list.index(resource)
            del resource_list[idx]
            # todo - verify requests.delete(...) is called
        
            self.assertFalse(resource in resource_list)
        
    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, User, "name", fixture_name='user')
    def testDeleteUserResourceByList(self, client, user, mock_service):
        return self._testDeleteResourceByList(client.users, user, mock_service)
    
    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Device, "name", "host", 5000, fixture_name='device')
    def testDeleteDeviceResourceByList(self, client, device, mock_service):
        return self._testDeleteResourceByList(client.devices, device, mock_service)
    
    @fixture(_mock_service)
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def testDeleteScheduleResourceByList(self, client, schedule, mock_service):
        return self._testDeleteResourceByList(client.schedules, schedule, mock_service)
    
    # TODO - phase...all of it
    
if __name__ == "__main__":
    import sys;sys.argv = ['', 'Test.testName']
    unittest.main()