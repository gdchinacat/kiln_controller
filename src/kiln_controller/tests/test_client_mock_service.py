"""
Tests the mock service used by client tests.
"""

from dataclasses import asdict
from http import HTTPStatus
from typing import Dict, List
from unittest import TestCase

from requests.models import Response

from kiln_controller.client import User
from kiln_controller.client.mock_service import (MockService, Resource,
                                                 NotFound)


def _obj(response: Response) -> Dict | List:
    """get the obj from the Response json"""
    return response.json()


class MockServiceTest(TestCase):

    def test_walk(self):
        child2 = Resource(id=2)
        child3 = Resource(id=3)
        parent = Resource({'child': Resource({'2': child2, '3': child3})},
                          id=1)
        service = MockService({'parent': Resource({'1': parent})},
                              live_service=False)

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
        service = MockService(live_service=False)

        self.assertEqual([], _obj(service.get("/user")))
        self.assertEqual([], _obj(service.get("/device")))
        self.assertEqual([], _obj(service.get("/schedule")))

    def test_post(self):
        service = MockService(live_service=False)

        user = asdict(User("name"))  # pylint: disable=not-callable
        created_user = _obj(service.post("/user", user))
        self.assertEqual(user, created_user)
        self.assertIsNotNone(created_user['id'], "created resource id not set")

        self.assertEqual(user, service.walk(f"/user/{user['id']}/"))
        self.assertEqual(user, _obj(service.get(f"/user/{user['id']}/")))

    def test_put(self):
        service = MockService(live_service=False)

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
        service = MockService({'parent': Resource({'1': parent})},
                              live_service=False)

        self.assertEqual({'id': 2}, _obj(service.get("/parent/1/child/2")))

        self.assertEqual(HTTPStatus.OK,
                         service.delete("/parent/1/child/2").status_code)
        self.assertEqual(HTTPStatus.NOT_FOUND,
                         service.get("/parent/1/child/2").status_code)

        # test that it's idempotent
        self.assertEqual(HTTPStatus.OK,
                         service.delete("/parent/1/child/2").status_code)
