import itertools
from collections import defaultdict
from collections.abc import Generator, Iterable
from typing import TYPE_CHECKING, ClassVar, Self

import fastapi
import httpx2
import pydantic
import pytest

from rest_client import (
    Resource,
    ResourceListDescriptor,
    RestClient,
    RootResourceList,
)

from ..conftest import ServiceFactory

type TestApp = fastapi.FastAPI


class _ChildCreate(pydantic.BaseModel):
    a: int


class _ChildPut(_ChildCreate): ...


class _ChildModel(pydantic.BaseModel):
    id: int
    a: int


class Child(Resource["Parent"]):
    _URL: ClassVar[str] = "/child"  # relative to parent

    a: int


class _ParentCreate(pydantic.BaseModel):
    a: int


class _ParentPut(_ParentCreate): ...


class _ParentModel(pydantic.BaseModel):
    id: int
    a: int


class Parent(Resource["TestClient"]):
    _URL: ClassVar[str] = "/parent"

    a: int
    children = ResourceListDescriptor(Child)


@pytest.fixture
def test_app() -> TestApp:
    app = fastapi.FastAPI()

    ids = itertools.count()
    parents: dict[int, _ParentModel] = {}
    children: defaultdict[int, dict[int, _ChildModel]] = defaultdict(
        dict[int, _ChildModel]
    )

    @app.post(Parent._URL)
    async def _create_parent(create: _ParentCreate) -> _ParentModel:
        parent = _ParentModel.model_validate(
            create.model_dump() | {"id": next(ids)}
        )
        parents[parent.id] = parent
        return parents[parent.id]

    @app.get(Parent._URL)
    async def _list_parents() -> Iterable[_ParentModel]:
        return parents.values()

    @app.get(Parent._URL + "/{_id}")
    async def _get_parent(_id: int) -> _ParentModel:
        if _id not in parents:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND
            )
        return parents[_id]

    @app.put(Parent._URL + "/{_id}")
    async def _put_parent(_id: int, put: _ParentPut) -> _ParentModel:
        if _id not in parents:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND
            )
        parent = parents[_id]
        for k, v in put.model_dump().items():
            setattr(parent, k, v)
        return parents[_id]

    @app.delete(Parent._URL + "/{_id}")
    async def _delete_parent(_id: int) -> dict[str, str]:
        parents.pop(_id, None)
        return {}

    @app.post(f"{Parent._URL}/{{parent_id}}{Child._URL}")
    async def _create_child(
        parent_id: int, create: _ChildCreate
    ) -> _ChildModel:
        if parent_id not in parents:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND
            )
        child = _ChildModel.model_validate(
            create.model_dump() | {"id": next(ids)}
        )
        children[parent_id][child.id] = child
        return children[parent_id][child.id]

    @app.get(f"{Parent._URL}/{{parent_id}}{Child._URL}")
    async def _list_children(parent_id: int) -> Iterable[_ChildModel]:
        if parent_id not in parents:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND
            )
        return children.get(parent_id, {}).values()

    @app.get(f"{Parent._URL}/{{parent_id}}{Child._URL}/{{child_id}}")
    async def _get_child(parent_id: int, child_id: int) -> _ChildModel:
        if parent_id not in children or child_id not in children[parent_id]:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND
            )
        return children[parent_id][child_id]

    @app.put(f"{Parent._URL}/{{parent_id}}{Child._URL}/{{child_id}}")
    async def _put_child(
        parent_id: int, child_id: int, put: _ChildPut
    ) -> _ChildModel:
        if parent_id not in children or child_id not in children[parent_id]:
            raise fastapi.HTTPException(
                status_code=fastapi.status.HTTP_404_NOT_FOUND
            )
        child = children[parent_id][child_id]
        for k, v in put.model_dump().items():
            setattr(child, k, v)
        return child

    @app.delete(f"{Parent._URL}/{{parent_id}}{Child._URL}/{{child_id}}")
    async def _delete_child(parent_id: int, child_id: int) -> dict[str, str]:
        if parent_id in children and child_id in children[parent_id]:
            del children[parent_id][child_id]
        return {}

    return app


class TestClient(RestClient):
    __test__ = False

    if TYPE_CHECKING:
        # Hide this at runtime so pydantic doesn't treat it as an attribute.
        parents: RootResourceList[Parent]

    def __init__(self, client: httpx2.Client) -> None:
        super().__init__(client)
        self.parents = RootResourceList(Parent, self)

    def expire(self) -> Self:
        self.parents.expire()
        return self


@pytest.fixture
def client(
    service_factory: ServiceFactory, test_app: fastapi.FastAPI
) -> Generator[TestClient]:
    with (
        service_factory(test_app) as service,
        httpx2.Client(
            base_url=service.url, verify=service.client_ssl_context
        ) as client,
    ):
        yield TestClient(client)
