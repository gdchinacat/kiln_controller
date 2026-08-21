"""
Framework for application resources.
"""

from abc import ABC
from functools import wraps
from http import HTTPStatus
from logging import getLogger
from typing import Callable, Dict

from fastapi import APIRouter
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy import select
from sqlalchemy.exc import NoResultFound, IntegrityError

from ..models.validators import ValidationError, PhaseType
from ..models import Session
from ..models.base import Base, MappedBase
from mypy_extensions import KwArg

__all__ = []


logger = getLogger("resource/base.py")


def error(msg: str) -> Dict[str, str]:
    """create a json error dict with error msg"""
    # TODO - don't expose internal error messages (500 returns sql error)
    return {"message": msg}


def _lookup(resource_type: type[Base], session: Session, id: int) -> resource_type:
    """lookup the resource by id"""
    try:
        query = select(resource_type).filter_by(id=id)
        return session.execute(query).scalar_one()
    except NoResultFound:
        return None


def create_router(
    resource_type: type[Base], orm_type: type[MappedBase], url_prefix=""
) -> APIRouter:
    """
    Base class for resources (abstract).

    Subclasses must override:
        - resource_type: the ORM type this resource handles.

    Provides a way to _lookup() resources of its resource_type.
    get(), post(), put(), and delete() endpoint methods to implement the CRUD
    operations for resource_type.
    """

    router = APIRouter(
        prefix=f"{url_prefix}/{resource_type._URL_PATH}", tags=[resource_type.__name__]
    )

    @router.get("/")
    async def _list_get(
        schedule_id=None, filters: dict = {}
    ):  # todo schedule_id and filters hack
        """get the list of resource_type resources"""
        query = select(orm_type)
        if schedule_id is not None:
            # theoretical hack - is fastapi not inserting schedule_id if not explicitly declared?
            filters["schedule_id"] = schedule_id
        if filters:
            query = query.filter_by(**filters)
        with Session() as session:
            return [
                orm.model_dump(mode="json") for orm in session.execute(query).scalars()
            ]

    @router.get("/{id}")
    async def _get(id: int, schedule_id=None) -> Dict:
        """get the resource"""
        with Session() as session:
            orm = _lookup(orm_type, session, id)
        if not orm:
            return (
                error(f"{self.resource_type.__name__} with id={id} not found"),
                HTTPStatus.NOT_FOUND,
            )
        return orm.model_dump(mode="json")

    @router.post("/")
    async def _post(resource: resource_type, schedule_id=None):
        """create a resource of resource_type"""
        if schedule_id is not None:  # Ugly Ugly Ugly hack TODO
            resource.schedule_id = schedule_id
        try:
            orm = orm_type.model_validate(resource)
            with (session := Session(expire_on_commit=False)), session.begin():
                session.add(orm)
                session.flush()
                orm.validate_create_or_update()
            return orm.model_dump(mode="json")
        except (ValidationError, PydanticValidationError):
            # todo - move all this exception handling into the app
            raise
        except IntegrityError as e:
            # todo - we should not be getting IntegrityErrors from the database
            #        since that indicates validation was lacking. But...that's
            #        going to happen, so handle it as a *client* error since
            #        the model is simple enough to make that a good assumption.
            # todo - don't expose internal details (e) to client
            return error(f"{e}"), HTTPStatus.UNPROCESSABLE_ENTITY
        except Exception as e:
            logger.exception(e)
            # todo - don't expose internal details (e) to client
            return error(f"{e}"), HTTPStatus.INTERNAL_SERVER_ERROR

    @router.put("/{id}")
    async def _put(id: int, resource: resource_type) -> Dict:
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

    @router.delete("/{id}")
    async def delete(id: int):
        """delete the resource"""
        with (session := Session()), session.begin():
            orm = _lookup(orm_type, session, id)
            if orm is not None:
                orm.validate_delete()
                session.delete(orm)
        return {}

    return router
