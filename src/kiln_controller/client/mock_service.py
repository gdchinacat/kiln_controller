"""
Implementes a mock service for use by unit testing.
"""
from contextlib import contextmanager
from dataclasses import asdict
from functools import wraps
from http import HTTPStatus
from itertools import count
from typing import Dict, List, Any
from unittest import TestCase
from unittest.mock import patch
from urllib.parse import urlparse

from requests.models import Response

from ..client import User


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
    resource: Dict
    sub_resources: Dict[str, "Resource"]

    def __init__(self, sub_resources: Dict[str, "Resource"] = None, **kwargs):
        self['resource'] = dict(kwargs)
        self['sub_resources'] = sub_resources or {}

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

        Since this patches client.requests *ALL* requests from the client
        module will be routed to the MockService.
        """
        with patch('kiln_controller.client.client.requests', new=self):
            yield self

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
            return action(resource)
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

        def _post(resource):
            resource.sub_resources[str(json['id'])] = Resource(**json)
            return json
        return self.walk(url, action=_post)

    @exception_to_response
    def put(self, url: str, json: Dict[str, Any], **_) -> Response:
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
    def delete(self, url: str, **_) -> Response:
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


def _obj(response: Response) -> Dict | List:
    """get the obj from the Response json"""
    return response.json()


class MockServiceTest(TestCase):

    def test_walk(self):
        child2 = Resource(id=2)
        child3 = Resource(id=3)
        parent = Resource({'child': Resource({'2': child2, '3': child3})},
                          id=1)
        service = MockService({'parent': Resource({'1': parent})})

        self.assertEqual([parent.resource], service.walk('/parent'))
        self.assertIs(parent.resource, service.walk('/parent/1'))
        self.assertEqual([child2.resource, child3.resource],
                         service.walk('/parent/1/child'))
        self.assertIs(child2.resource,
                      service.walk('/parent/1/child/2'))
        self.assertIs(child3.resource,
                      service.walk('/parent/1/child/3'))

        self.assertRaises(NotFound, service.walk, '/parent/2')
        self.assertRaises(NotFound, service.walk, '/nonexistent')

    def test_default_service(self):
        service = MockService()

        self.assertEqual([], _obj(service.get("/user")))
        self.assertEqual([], _obj(service.get("/device")))
        self.assertEqual([], _obj(service.get("/schedule")))

    def test_post(self):
        service = MockService()

        user = asdict(User("name"))  # pylint: disable=not-callable
        created_user = _obj(service.post("/user", user))
        self.assertEqual(user, created_user)
        self.assertIsNotNone(created_user['id'], "created resource id not set")

        self.assertEqual(user, service.walk(f"/user/{user['id']}/"))
        self.assertEqual(user, _obj(service.get(f"/user/{user['id']}/")))

    def test_put(self):
        service = MockService()

        _id = str(next(service.ids))
        user = asdict(User("name"))  # pylint: disable=not-callable
        created_user = _obj(service.put(f"/user/{_id}", user))
        self.assertEqual(user, created_user)

        self.assertEqual(user, service.walk(f"/user/{user['id']}/"))
        self.assertEqual(user, _obj(service.get(f"/user/{user['id']}/")))

        # change an attribute
        user['email'] = "email"
        self.assertEqual(HTTPStatus.OK,
                         service.put(f"/user/{_id}", user).status_code)
        self.assertEqual(user, _obj(service.get(f"/user/{user['id']}/")))

    def test_delete(self):
        child2 = Resource(id=2)
        child3 = Resource(id=3)
        parent = Resource({'child': Resource({'2': child2,
                                              '3': child3})},
                          id=1)
        service = MockService({'parent': Resource({'1': parent})})

        self.assertEqual({'id': 2}, _obj(service.get("/parent/1/child/2")))

        self.assertEqual(HTTPStatus.OK,
                         service.delete("/parent/1/child/2").status_code)
        self.assertEqual(HTTPStatus.NOT_FOUND,
                         service.get("/parent/1/child/2").status_code)

        # test that it's idempotent
        self.assertEqual(HTTPStatus.OK,
                         service.delete("/parent/1/child/2").status_code)
