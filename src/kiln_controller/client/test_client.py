import unittest
from . import Client, User, Device, Schedule
import traceback
import random
from contextlib import contextmanager
from skytap.fixtures import fixture, default_fixture_name, pass_self

class ClientTest(unittest.TestCase):
    """
    Currently requires the service to be running at the default url for the
    client (localhost:5000) and be ok with it mucking with.
    It does *try* to clean up after itself, even when there are failures,
    but no guarantees.
    """
    def testClientInit(self):
        client = Client()
    
    @staticmethod
    def cleanup(func):
        def wrap(self, *args, **kwargs):
            objs = func(self, *args, **kwargs)
            try:
                for obj in objs:
                    obj.delete()
            except Exception as e:
                # Don't fail the test, but don't simply eat the exception,
                # dump it to console.
                traceback.print_exception(e)
        return wrap
                    
    @cleanup
    def _testListAdd(self, _type_list_getter, *args, iadd=False):
        """
        helper to add an object.
        _type_list_getter: (_type, list_getter)
        
        list_getter: func(client) -> ResourceList
        iadd: bool: use += as opposed to .append?
        """
        
        # unpack the arg telling us what to add and where to add it
        _type, list_getter = _type_list_getter
        client = Client()
        _list = list_getter(client)
        
        # create the resource
        obj = _type(*args)
        
        #add it to the list
        if iadd:
            _list += obj
        else:
            _list.append(obj)
        
        # make sure the obj exists
        self.assertTrue(obj in _list, f"{obj} not in {_list}")
        
        # get a new client, make sure it exists there as well
        client = Client()
        _list = list_getter(client)
        self.assertTrue(obj in _list)
        return (obj,)
    
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

    @cleanup
    def _testPost(self, resource):
        """test that resources of type _type can be created using Resource.post(client)"""
        self.assertIsNone(resource.id)  #precondition check
        
        client = Client()
        
        # test post success
        resource.post(client)
        self.assertIsNotNone(resource.id, "post failed to assign id to resource")
        
        # test post with resource.id fails
        self.assertRaises(AttributeError, resource.post, client)
        
        return (resource,)
    
    def testPostUser(self):
        return self._testPost(User("name"))
        
    def testPostDevice(self):
        return self._testPost(Device("name", "host", 5000))
        
    def testPostSchedule(self):
        return self._testPost(Schedule("name"))
        
    @cleanup
    def _testPut(self, resource):
        """
        test that resources of type _type can be created and updated using
        Resource.put(client)
        
        """
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
        
        return (resource,)
    
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
        
    @default_fixture_name('client')
    @pass_self
    def _client(self, **_):
        return Client()
    
    @pass_self
    def _resource(self, _type, *args, client, **kwargs):
        """
        create a resource of the given _type using client.
        """
        resource = _type(*args, **kwargs)
        resource.post(client)
        return resource
        
    def _testDeleteResource(self, resource):
        """test that Resource.delete() functions"""
        self.assertIsNotNone(resource.id)
        resource.delete()
        # todo - verify requests.delete(...) is called
        self.assertIsNone(resource.id)
    
    @fixture(_client)
    @fixture(_resource, User, "name", fixture_name='user')
    def testDeleteUserResource(self, client, user):
        return self._testDeleteResource(user)
    
    @fixture(_client)
    @fixture(_resource, Device, "name", "host", 5000, fixture_name='device')
    def testDeleteDeviceResource(self, client, device):
        return self._testDeleteResource(device)
    
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def testDeleteScheduleResource(self, client, schedule):
        return self._testDeleteResource(schedule)
    
    def _testDeleteResourceByList(self, resource_list, resource):
        """test that Resource.delete() functions"""
        
        resource_list.refresh() # ensure the view is in sync with resource
        
        self.assertTrue(resource in resource_list)
        
        idx = resource_list.index(resource)
        del resource_list[idx]
        # todo - verify requests.delete(...) is called
        
        self.assertIsNone(resource.id)
        resource_list.refresh()
        self.assertRaiseS(Exception, resource.refresh)
        self.assertFalse(resource in resource_list)
        
    @fixture(_client)
    @fixture(_resource, User, "name", fixture_name='user')
    def testDeleteUserResourceByList(self, client, user):
        return self._testDeleteResourceByList(client.users, user)
    
    @fixture(_client)
    @fixture(_resource, Device, "name", "host", 5000, fixture_name='device')
    def testDeleteDeviceResourceByList(self, client, device):
        return self._testDeleteResourceByList(client.devices, device)
    
    @fixture(_client)
    @fixture(_resource, Schedule, "name", fixture_name='schedule')
    def testDeleteScheduleResourceByList(self, client, schedule):
        return self._testDeleteResourceByList(client.schedules, schedule)
    
    # TODO - phase...all of it
    
if __name__ == "__main__":
    import sys;sys.argv = ['', 'Test.testName']
    unittest.main()