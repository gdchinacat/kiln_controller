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


class _RootCreate(pydantic.BaseModel):
    a: int


class _RootPut(_RootCreate): ...


class _RootModel(pydantic.BaseModel):
    id: int
    a: int


class Root(Resource):
    _URL: ClassVar[str] = "/root"

    a: int


@pytest.fixture
def test_app() -> TestApp:
    app = fastapi.FastAPI()

    ids = itertools.count()
    roots: dict[int, _RootModel] = {}

    @app.post(Root._URL)
    async def _create_root(create: _RootCreate) -> _RootModel:
        root = _RootModel.model_validate(create.model_dump() | {"id": next(ids)})
        roots[root.id] = root
        return roots[root.id]

    @app.get(Root._URL)
    async def _list_roots() -> Iterable[_RootModel]:
        return roots.values()

    @app.get(Root._URL + "/{_id}")
    async def _get_root(_id: int) -> _RootModel:
        if _id not in roots:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        return roots[_id]

    @app.put(Root._URL + "/{_id}")
    async def _put_root(_id: int, put: _RootPut) -> _RootModel:
        if _id not in roots:
            raise fastapi.HTTPException(status_code=fastapi.status.HTTP_404_NOT_FOUND)
        root = roots[_id]
        for k, v in put.model_dump().items():
            setattr(root, k, v)
        return roots[_id]

    @app.delete(Root._URL + "/{_id}")
    async def _delete_root(_id: int) -> dict[str, str]:
        del roots[_id]
        return {}

    return app


class TestClient(RestClient):
    __test__ = False
    roots: ResourceList[Root, None]

    def __init__(self, client: httpx2.Client):
        super().__init__(client)
        self.roots = ResourceList[Root, None](Root, self)

    def expire(self) -> Self:
        self.roots.expire()
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
