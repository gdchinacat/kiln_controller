from collections.abc import Generator, Iterable
import itertools

import fastapi
import httpx2
import pydantic
import pytest
from typing import Any, Self, ClassVar

from rest_client import Resource, ResourceList, RestClient

from ..conftest import ServiceFactory

type TestApp = fastapi.FastAPI


class _ParentCreate(pydantic.BaseModel):
    a: int


class _ParentPut(_ParentCreate): ...


class _ParentModel(pydantic.BaseModel):
    id: int
    a: int


class Parent(Resource):
    _URL: ClassVar[str] = "/parent"

    a: int


@pytest.fixture
def test_app() -> TestApp:
    app = fastapi.FastAPI()

    ids = itertools.count()
    parents: dict[int, _ParentModel] = {}

    @app.post(Parent._URL)
    async def _create_parent(create: _ParentCreate) -> _ParentModel:
        parent = _ParentModel.model_validate(create.model_dump() | {"id": next(ids)})
        parents[parent.id] = parent
        return parents[parent.id]

    @app.get(Parent._URL)
    async def _list_parents() -> Iterable[_ParentModel]:
        return parents.values()

    @app.get(Parent._URL + "/{_id}")
    async def _get_parent(_id: int) -> _ParentModel:
        if _id not in parents:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        return parents[_id]

    @app.put(Parent._URL + "/{_id}")
    async def _put_parent(_id: int, put: _ParentPut) -> _ParentModel:
        if _id not in parents:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        parent = parents[_id]
        for k, v in put.model_dump().items():
            setattr(parent, k, v)
        return parents[_id]

    @app.delete(Parent._URL + "/{_id}")
    async def _delete_parent(_id: int) -> dict[str, str]:
        del parents[_id]
        return {}

    return app


class TestClient(RestClient):
    __test__ = False
    parents: ResourceList[Parent, None]

    def __init__(self, client: httpx2.Client):
        super().__init__(client)
        self.parents = ResourceList[Parent, None](Parent, self)

    def expire(self) -> Self:
        self.parents.expire()
        return self


@pytest.fixture
def client(
    service_factory: ServiceFactory, test_app: fastapi.FastAPI
) -> Generator[TestClient]:
    with service_factory(test_app) as service:
        with httpx2.Client(
            base_url=service.url, verify=service.client_ssl_context
        ) as client:
            yield TestClient(client)
