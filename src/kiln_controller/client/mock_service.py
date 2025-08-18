"""
Implementes a mock service for use by unit testing.
"""
from unittest import mock, TestCase
from typing import Dict, List
from urllib.parse import urlparse
from requests.models import Response
from http import HTTPStatus

class Resource(dict):
    """
    Resource is used to build the mock resource model. It is a node in a tree.
    It has a set of attributes for the resource (.resource) as well as
    a collection of sub resources indexed by the path in the url to access that
    node.
    """
    resource: Dict
    sub_resources: Dict[str, "Resource"]
    
    def __init__(self, sub_resources: Dict[str, "Resource"]=None, **kwargs):
        self['resource'] = dict(kwargs)
        self['sub_resources'] = sub_resources or dict()
    
    @property
    def resource(self):
        return self['resource']
    
    @property
    def sub_resources(self):
        return self['sub_resources']
    
class MockService(Resource):
    
    def __init__(self, sub_resources:Dict[str, Resource]= None):
        self['sub_resources'] = sub_resources or {_type: Resource() for _type in 
                    ('users', 'devices', 'schedules')}
    
    def response(self, status_code):
        response = Response()
        response.status_code = status_code
        return response
    
    def walk(self, paths: List[str]):
        resource = self
        for path in paths:
            if path not in resource.sub_resources:
                return self.response(HTTPStatus.NOT_FOUND)
            resource = resource.sub_resources[path]
            
        # If the resource attributes contains 'id' then we found an actual
        # resource. If not, it's a collection of resources.
        if 'id' in resource.resource:
            return resource.resource
        else:
            return [x.resource for x in resource.sub_resources.values()]
            
    def get_paths(self, url):
        parsed = urlparse(url)
        return parsed.path.split('/')
    
    def get(self, url):
        return self.walk_resources(self.get_paths(url))
    
class MockServiceTest(TestCase):
    def testMockService(self):
        child2 = Resource(id=2)
        child3 = Resource(id=3)
        parent = Resource({'child': Resource({'2': child2, '3': child3})}, id=1)
        service = MockService({'parent': Resource({'1': parent})})
        
        self.assertEqual([parent.resource], service.walk(('parent',)))
        self.assertIs(parent.resource, service.walk(('parent', '1')))
        self.assertEqual([child2.resource, child3.resource],
                         service.walk(('parent', '1', 'child')))
        self.assertIs(child2.resource,
                      service.walk(('parent', '1', 'child', '2')))
        self.assertIs(child3.resource,
                      service.walk(('parent', '1', 'child', '3')))
        
        self.assertEqual(HTTPStatus.NOT_FOUND, service.walk(('parent', '2')).status_code)
        self.assertEqual(HTTPStatus.NOT_FOUND, service.walk(('nonexistent')).status_code)
        