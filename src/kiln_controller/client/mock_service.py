"""
Implements a mock service for use by unit testing.
"""
from contextlib import contextmanager
from dataclasses import dataclass
from functools import wraps
from http import HTTPStatus
from itertools import count
import os
from typing import Dict, List, Any, Callable
from unittest.mock import patch
from urllib.parse import urlparse

import requests


class _HTTPError(Exception):
    status_code = None  # subclasses must override this


class NotFound(_HTTPError):
    status_code = HTTPStatus.NOT_FOUND


class Resource(dict):
    """
    Resource is used to build the mock resource model. It is a node in a tree.
    It has a set of attributes for the resource (.resource) as well as
    a collection of sub resources indexed by the path in the url to access that
    node.
    """
    TYPES: Dict[str, type] = {}
    resource: Dict
    sub_resources: Dict[str, "Resource"]

    def __init__(self, sub_resources: Dict[str, "Resource"] = None, **kwargs):
        self['resource'] = dict(kwargs)
        self['sub_resources'] = sub_resources or {}

    @classmethod
    def create(cls,
               resource_type: str,
               **kwargs):
        '''create a new resource of the indicated type'''
        resource_cls = cls.TYPES.get(resource_type, cls)
        return resource_cls(**kwargs)

    @property
    def resource(self):
        return self['resource']

    @property
    def sub_resources(self):
        return self['sub_resources']


class ScheduleResource(Resource):
    def __init__(self, *args, **kwargs):
        sub_resources = {'phase': Resource()}
        super().__init__(*args, sub_resources=sub_resources, **kwargs)


Resource.TYPES['schedule'] = ScheduleResource


@dataclass
class Call:
    '''a call to a mocked function'''
    method: Callable
    args: List[Any]
    kwargs: Dict[str, Any]
    return_: Any = None
    exception: Exception = None


class MockService(Resource):

    calls: List[Call]

    @staticmethod
    def track_call(func):
        '''decorator to append the call to the list of calls'''
        @wraps(func)
        def _track_call(self, *args, **kwargs):
            call = Call(func.__name__, args, kwargs)
            self.calls.append(call)
            try:
                ret = func(self, *args, **kwargs)
                if self.live_service:
                    call.return_ = ret.json()
                else:
                    call.return_ = ret
                return ret
            except Exception as exception:
                call.exception = exception
                raise
        return _track_call

    @staticmethod
    def conditional_requests_mock(requests_func):
        '''decorator that mocks requests_func only when live_service=false'''
        def dec(mock_func):
            @wraps(mock_func)
            def _conditional_requests_mock(self, *args, **kwargs):
                if self.live_service:
                    return requests_func(*args, **kwargs)
                else:
                    return mock_func(self, *args, **kwargs)
            return _conditional_requests_mock
        return dec

    @contextmanager
    def patch(self):
        """
        Context manager that patches client.requests to intercept calls for
        call tracking. The mock functions should be decorated with
        @conditional_requests_mock to permit tests to execute against a live service.
        """
        with patch('kiln_controller.client.client.requests', new=self):
            self.calls = []  # only track calls in this with block
            yield self

    def __init__(self, sub_resources: Dict[str, Resource] = None,
                 live_service: bool = None):
        super().__init__()
        self['sub_resources'] = (sub_resources or
                                 {_type: Resource() for _type in
                                  ('user', 'device', 'schedule')})
        self.ids = count()
        self.calls = []
        self.live_service = (
            os.getenv('LIVE_SERVICE', 'false').upper() == 'TRUE'
            if live_service is None else live_service)

    def response(self, status_code, obj: Dict = None) -> requests.Response:
        response = requests.Response()
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
        if action:
            return action(paths, resource)
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
                if self.live_service:
                    return ret
                else:
                    return self.response(HTTPStatus.OK, ret)
            except _HTTPError as e:
                return self.response(e.status_code,
                                     {'message': e.args[0]})
        return wrap

    @exception_to_response
    @track_call
    @conditional_requests_mock(requests.get)
    def get(self, url, **_) -> requests.Response:
        return self.walk(url)

    @exception_to_response
    @track_call
    @conditional_requests_mock(requests.post)
    def post(self, url: str, json: Dict[str, Any], **_) -> requests.Response:
        json['id'] = next(self.ids)

        def create_resource(paths, parent):
            resource_type = paths[-1]
            assert resource_type, f"{resource_type=}"
            parent.sub_resources[str(json['id'])] = Resource.create(
                resource_type, **json)
            return json
        return self.walk(url, action=create_resource)

    @exception_to_response
    @track_call
    @conditional_requests_mock(requests.put)
    def put(self, url: str, json: Dict[str, Any], **_) -> requests.Response:
        # get the id from the url and store it on the obj
        paths = self.get_paths(url)
        json['id'] = int(paths[-1])

        # find the parent, makes handling not existing easier
        url = "/".join(paths[:-1])

        def _put(paths, parent_resource):
            # todo - whatever post does to create typed resources
            parent_resource.sub_resources[str(json['id'])] = Resource(**json)
            return json
        return self.walk(url, action=_put)

    @exception_to_response
    @track_call
    @conditional_requests_mock(requests.delete)
    def delete(self, url: str, **_) -> requests.Response:
        # get the id from the url and store it on the obj
        paths = self.get_paths(url)
        _id = paths[-1]

        # find the parent, it's the one that needs updating
        url = "/".join(paths[:-1])

        def _delete(paths, parent_resource):
            if _id in parent_resource.sub_resources:
                del parent_resource.sub_resources[_id]
            return {}
        return self.walk(url, action=_delete)
