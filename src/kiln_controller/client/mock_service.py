"""
Implementes a mock service for use by unit testing.
"""
from contextlib import contextmanager
from functools import wraps
from http import HTTPStatus
from itertools import count
from requests.models import Response
from typing import Dict, List, Any
from unittest.mock import patch
from urllib.parse import urlparse

class _HTTPError(Exception): ...
class NotFound(_HTTPError):
    status_code = HTTPStatus.NOT_FOUND

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
   
    @contextmanager
    def patch(self):
        """
        Context manager that patches client.requests to use an instance of
        MockService rather than making request calls.
        
        Since this patches client.requests *ALL* requests from the client module
        will be routed to the MockService.
        """
        with patch('kiln_controller.client.client.requests', new=self):
            yield self
    
    def __init__(self, sub_resources:Dict[str, Resource]= None):
        self['sub_resources'] = sub_resources or {_type: Resource() for _type in 
                    ('user', 'device', 'schedule')}
        self.ids = count()
    
    def response(self, status_code, obj: Dict = None) -> Response:
        response = Response()
        response.status_code = status_code
        if obj is not None:
            response.json = lambda: obj
        return response
    
    def walk(self, url: str, action=None):
        """
        Walk the resource tree.
        If action is set it is called with a single argument, the
        found resource, and its return value becomes the object
        returned for the walk.
        """
        
        paths: List[str] = self.get_paths(url)
        
        resource = self
        for path in paths:
            if path not in resource.sub_resources:
                raise NotFound(url)
            resource = resource.sub_resources[path]
            
        # If the resource attributes contains 'id' then we found an actual
        # resource. If not, it's a collection of resources.
        if 'id' in resource.resource:
            ret = resource.resource
            if action:
                ret = action(ret)
            return ret
        else:
            if action:
                return action(resource)
            else:
                return [x.resource for x in
                                  resource.sub_resources.values()]
            
    def get_paths(self, url):
        parsed = urlparse(url)
        paths = parsed.path.split('/')
        if paths[0] == '':
            paths = paths[1:]
        if paths[-1] == '':
            paths = paths[:-1]
        return paths
    
    @staticmethod
    def exception_to_response(func):
        @wraps(func)
        def wrap(self, *args, **kwargs):
            try: 
                ret = func(self, *args, **kwargs)
                return self.response(HTTPStatus.OK, ret)
            except _HTTPError as e:
                return self.response(e.status_code,
                                     {'message': e.args[0]})
        return wrap
        
    @exception_to_response
    def get(self, url) -> Response:
        return self.walk(url)
    
    @exception_to_response
    def post(self, url:str, json: Dict[str, Any]) -> Response:
        json['id'] = next(self.ids)
        
        def _post(resource):
            resource.sub_resources[str(json['id'])] = Resource(**json)
            return json
        return self.walk(url, action=_post)
        return json
    
    @exception_to_response
    def put(self, url:str, json: Dict[str, Any]) -> Response:
        # get the id from the url and store it on the obj
        paths = self.get_paths(url)
        json['id'] = int(paths[-1])
        
        # find the parent, makes handling not existing easier
        url = "/".join(paths[:-1])
        
        def _put(parent_resource):
            parent_resource.sub_resources[str(json['id'])] = Resource(**json)
            return json
        return self.walk(url, action=_put)
    
    @exception_to_response
    def delete(self, url:str) -> Response:
        # get the id from the url and store it on the obj
        paths = self.get_paths(url)
        _id = paths[-1]
        
        # find the parent, it's the one that needs updating
        url = "/".join(paths[:-1])
        
        def _delete(parent_resource):
            if _id in parent_resource.sub_resources:
                del parent_resource.sub_resources[_id]
            return {}
        return self.walk(url, action=_delete)
        
        