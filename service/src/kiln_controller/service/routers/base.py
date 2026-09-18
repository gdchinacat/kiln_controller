"""
Framework for application resources.
"""

from abc import ABC
from functools import wraps
from http import HTTPStatus
from logging import getLogger
from typing import Callable, Dict

from fastapi import Depends, Request, Response, status, HTTPException, APIRouter
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import pydantic
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, IntegrityError
import sqlmodel

from ...common.validators import ValidationError, ValidationErrors
from ..models import Session, User, UserORM, ResourceCreate

__all__ = []


logger = getLogger("resource/base.py")


security = HTTPBasic()


async def authenticate_user(
    credentials: HTTPBasicCredentials = Depends(security),
) -> UserORM:
    with Session() as session:
        query = select(UserORM).filter_by(username=credentials.username)
        user = session.execute(query).scalar_one_or_none()

        if not user or user.password != credentials.password:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

        return user


def _apply_resource_type[**P, R](
    resource_type: str,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """format the decorated functions __doc__ with kwargs"""

    def dec(func: Callable[P, R]) -> Callable[P, R]:
        assert func.__doc__, f"{func} does not have a __doc__ to format"
        func.__doc__ = func.__doc__.format(resource_type=resource_type)
        func.__name__ = func.__name__ + "_" + resource_type
        return func

    return dec


def create_router(
    url_path: str,
    resource_type: type[pydantic.BaseModel],
    orm_type: type[sqlmodel.SQLModel],
    url_prefix="",
    resource_create_type: type[ResourceCreate] | None = None,
    resource_create_response_type: type[pydantic.BaseModel] | None = None,
    resource_update_type: type[pydantic.BaseModel] | None = None,
) -> APIRouter:
    """
    Base class for resources (abstract).

    Subclasses must override:
        - resource_type: the ORM type this resource handles.

    Provides a way to lookup resources of its resource_type.
    get(), post(), put(), and delete() endpoint methods to implement the CRUD
    operations for resource_type.
    """
    resource_create_type = resource_create_type or resource_type
    resource_create_response_type = resource_create_response_type or resource_type
    resource_update_type = resource_update_type or resource_type
    router = APIRouter(prefix=f"{url_prefix}/{url_path}", tags=[resource_type.__name__])

    @router.get("/")
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _list(
        request: Request, user: User = Depends(authenticate_user)
    ) -> list[resource_type]:
        """get the list of {resource_type}s"""
        query = select(orm_type)
        if request.path_params:  # schedule_id in '/schedule/{request_id}/phase
            query = query.filter_by(**request.path_params)
        with Session() as session:
            return [
                orm.model_dump(mode="json") for orm in session.execute(query).scalars()
            ]

    @router.get("/{id}")
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _get(id: int, user: User = Depends(authenticate_user)) -> resource_type:
        """get a {resource_type}"""
        with Session() as session:
            orm = session.get(orm_type, id)
        if not orm:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)

        return orm.model_dump(mode="json")

    @router.post(
        "/",
        status_code=HTTPStatus.CREATED,
        response_model=resource_create_response_type,
    )
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _create(
        request: Request,
        resource: resource_create_type,
        user: User = Depends(authenticate_user),
    ) -> resource_create_response_type:
        """create a {resource_type}"""
        resource_dict = resource.model_dump()
        resource_dict.update(request.path_params)
        resource_dict.update(resource.extra_attrs(user))
        orm = orm_type.model_validate(resource_dict)
        with (session := Session(expire_on_commit=False)), session.begin():
            session.add(orm)
            session.flush()
            orm.validate_create_or_update()
        # return resource_create_response_type.model_validate(orm.model_dump(mode="json"))
        return orm.model_dump(mode="json")

    @router.put("/{id}")
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _update(
        id: int,
        resource: resource_update_type,
        user: User = Depends(authenticate_user),
    ) -> resource_type:
        """Update the {resource_type}."""
        """
        There is some debate in the REST community as to whether or not clients
        should be allowed to create resources with PUT since it gives the
        client control over what id should be used. If a client decides to use
        id=1 and a resource exists with id=1 the service has no way to tell if
        the client intended to create a new entity or update the existing
        entity, so the PUT succeeds, possibly clobbering an entity it didn't
        intend to clobber. However...a naive reading of what PUT should do
        allows resources to be created by id. That is the current
        implementation.

        So, why not just require POST be used? There is no way to idempotently
        create the resource since the client doesn't know how to identify it...
        if the request fails after the resource is created the client doesn't
        know what the id is. The only way to proceed is to retry the POST,
        which may create spurious resources.

        So, how do "real" services handle this? Add a resource to assign ids in
        a way that it will *never* hand out the same id twice. Before doing a
        PUT clients request an id to use for the resource to create using PUT.
        This has vulnerabilities if clients or caches are malicious or buggy
        since they may try to reuse an id leading to resource clobbering. So,
        you increase the complexity to what amounts to a two-phase commit
        protocol where you also provide a "create-by-id authorization token"
        that is removed once it is used, and PUT requires the token exist when
        creating through PUT.

        This service doesn't need that level of complexity, so, for now, it
        allows create through POST or create-with-id through PUT. Clients are
        trusted and assumed to not be buggy. This will be revisited if it is
        shown to be a problem

        TODO - update the service to reject creation of resources using PUT and
               require all clients to use POST to remove the possibility that
               clients will clobber existing entities.
        Create or update a resource by id.
        """
        with (session := Session(expire_on_commit=False)), session.begin():
            orm = session.get(orm_type, id)
            if not orm:
                resource_dict = resource.model_dump()
                resource_dict["id"] = id
                orm = orm_type.model_validate(resource_dict)
                session.add(orm)
            else:
                orm.sqlmodel_update(resource.model_dump(exclude_unset=True))
        return orm.model_dump(mode="json")

    @router.delete(
        "/{id}",
        status_code=status.HTTP_204_NO_CONTENT,
        response_class=Response,
    )
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _delete(
        id: int,
        user=Depends(authenticate_user),
    ) -> None:
        """delete a {resource_type}"""
        with (session := Session()), session.begin():
            orm = session.get(orm_type, id)
            if orm is not None:
                orm.validate_delete()
                session.delete(orm)

    return router
