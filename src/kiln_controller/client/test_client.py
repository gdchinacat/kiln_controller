import unittest
from . import Client, User, Device, Schedule

class ClientTest(unittest.TestCase):
    """
    currently requires the server to be running and be ok with it mucking with
    it.
    """
    def testClientInit(self):
        client = Client()
    
    def _testAdd(self, _type_list_getter, *args):
        """
        helper to add an object.
        _type_list_getter: (_type, list_getter)
        
        list_getter: func(client) -> ResourceList
        """
        
        _type, list_getter = _type_list_getter
        client = Client()
        _list = list_getter(client)
        obj = _type(*args)
        _list += obj
        
        # make sure the obj exists
        self.assertTrue(obj in _list, f"{obj} not in {_list}")
        
        # get a new client, make sure it exists there as well
        client = Client()
        _list = list_getter(client)
        self.assertTrue(obj in _list)
        return obj
    
    def testAddUser(self):
        return self._testAdd((User, lambda client: client.users),
                             "name")
    
    def testAddDevice(self):
        return self._testAdd((Device, lambda client: client.devices),
                             "name", "host", 5000, 'description')
        
    def testAddSchedule(self):
        return self._testAdd((Schedule, lambda client: client.schedules),
                             "name")
        
        
        
if __name__ == "__main__":
    import sys;sys.argv = ['', 'Test.testName']
    unittest.main()