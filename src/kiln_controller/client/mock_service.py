"""
Implements a mock service for use by unit testing.
"""
from contextlib import contextmanager
from functools import wraps
from http import HTTPStatus
from itertools import count
import os
from typing import Dict, List, Any
from unittest.mock import patch
from urllib.parse import urlparse

from requests.models import Response


class _HTTPError(Exception):
    status_code = None  # subclasses must override this


live_service = os.getenv('LIVE_SERVICE', 'false').upper() == 'TRUE'


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


class MockService(Resource):

    @contextmanager
    def patch(self):
        """
        Context manager that patches client.requests to use an instance of
        MockService rather than making request calls.

        Since this patches client.requests *ALL* requests from the client
        module will be routed to the MockService.
        """
        if not live_service:
            with patch('kiln_controller.client.client.requests', new=self):
                yield self
        else:
            yield None

    def __init__(self, sub_resources: Dict[str, Resource] = None):
        super().__init__()
        self['sub_resources'] = (sub_resources or
                                 {_type: Resource() for _type in
                                  ('user', 'device', 'schedule')})
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
                return self.response(HTTPStatus.OK, ret)
            except _HTTPError as e:
                return self.response(e.status_code,
                                     {'message': e.args[0]})
        return wrap

    @exception_to_response
    def get(self, url, **_) -> Response:
        return self.walk(url)

    @exception_to_response
    def post(self, url: str, json: Dict[str, Any], **_) -> Response:
        json['id'] = next(self.ids)

        def create_resource(paths, parent):
            resource_type = paths[-1]
            assert resource_type, f"{resource_type=}"
            parent.sub_resources[str(json['id'])] = Resource.create(
                resource_type, **json)
            return json
        return self.walk(url, action=create_resource)

    @exception_to_response
    def put(self, url: str, json: Dict[str, Any], **_) -> Response:
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
    def delete(self, url: str, **_) -> Response:
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
