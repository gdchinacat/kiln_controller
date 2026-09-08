"""
Framework for application resources.
"""

from abc import ABC
from functools import wraps
from http import HTTPStatus
from logging import getLogger
from typing import Callable, Dict

import fastapi
from mypy_extensions import KwArg
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, IntegrityError

from ..models import Session
from ..models.base import Base, MappedBase
from ..models.validators import PhaseType

__all__ = []


logger = getLogger("resource/base.py")


def _lookup(resource_type: type[Base], session: Session, id: int) -> resource_type:
    """lookup the resource by id"""
    try:
        query = select(resource_type).filter_by(id=id)
        return session.execute(query).scalar_one()
    except NoResultFound:
        return None


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
    resource_type: type[Base], orm_type: type[MappedBase], url_prefix=""
) -> fastapi.APIRouter:
    """
    Base class for resources (abstract).

    Subclasses must override:
        - resource_type: the ORM type this resource handles.

    Provides a way to _lookup() resources of its resource_type.
    get(), post(), put(), and delete() endpoint methods to implement the CRUD
    operations for resource_type.
    """

    router = fastapi.APIRouter(
        prefix=f"{url_prefix}/{resource_type._URL_PATH}", tags=[resource_type.__name__]
    )

    @router.get("/")
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _list(request: fastapi.Request) -> list[resource_type]:
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
    async def _get(id: int, schedule_id=None) -> resource_type:
        """get a {resource_type}"""
        with Session() as session:
            orm = _lookup(orm_type, session, id)
        if not orm:
            return (
                fastapi.Response(
                    status_code=HTTPStatus.NOT_FOUND,
                    content={
                        "message": f"{resource_model.__name__} with id={id} not found"
                    },
                ),
            )
        return orm.model_dump(mode="json")

    @router.post("/", status_code=HTTPStatus.CREATED)
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _create(
        request: fastapi.Request, resource: resource_type
    ) -> resource_type:
        """create a {resource_type}"""
        # set the path parameter values on the resource (ie schedule_id on phase)
        for k, v in request.path_params.items():
            setattr(resource, k, v)
        orm = orm_type.model_validate(resource)
        with (session := Session(expire_on_commit=False)), session.begin():
            session.add(orm)
            session.flush()
            orm.validate_create_or_update()
        return orm.model_dump(mode="json")

    @router.put("/{id}")
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _update(id: int, resource: resource_type) -> resource_type:
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
        orm = orm_type.model_validate(resource)
        with (session := Session()), session.begin():
            session.merge(orm)
        return orm.model_dump(mode="json")

    @router.delete(
        "/{id}",
        status_code=fastapi.status.HTTP_204_NO_CONTENT,
        response_class=fastapi.Response,
    )
    @_apply_resource_type(resource_type=resource_type.__name__)
    async def _delete(id: int) -> None:
        """delete a {resource_type}"""
        with (session := Session()), session.begin():
            orm = _lookup(orm_type, session, id)
            if orm is not None:
                orm.validate_delete()
                session.delete(orm)

    return router
