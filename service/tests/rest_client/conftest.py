from collections.abc import Generator
import itertools

import fastapi
import httpx2
import pydantic
import pytest
from typing import Any

from rest_client import Resource

from ..conftest import ServiceFactory

type TestApp = fastapi.FastAPI
type TestClient = httpx2.Client


class _RootCreate(pydantic.BaseModel):
    a: int


class _RootPut(_RootCreate): ...


class _RootModel(pydantic.BaseModel):
    id: int
    a: int


class Root(Resource):
    _URL = "/root"

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


@pytest.fixture
def client(
    service_factory: ServiceFactory, test_app: fastapi.FastAPI
) -> Generator[httpx2.Client]:
    with service_factory(test_app) as service:
        with httpx2.Client(
            base_url=service.url, verify=service.client_ssl_context
        ) as client:
            yield client
