"""
Framework for application resources.
"""

from abc import ABC
from functools import wraps
from http import HTTPStatus
from logging import getLogger
from typing import Callable, Dict

from flask import current_app, request
from flask_restful import Resource
from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.exc import NoResultFound, IntegrityError

from ...common import ValidationError
import sqlalchemy

__all__ = []


logger = getLogger("resource/base.py")


def db(func) -> Callable[[Callable], Callable]:
    """decorator to inject the database into wrapped calls as db_= kwarg"""

    @wraps(func)
    def wrap(*args, **kwargs):
        db_ = current_app.db  # @UndefinedVariable
        return func(*args, **kwargs, db_=db_)

    return wrap


def error(msg: str) -> Dict[str, str]:
    """create a json error dict with error msg"""
    # TODO - don't expose internal error messages (500 returns sql error)
    return {"message": msg}


class BaseResource(Resource, ABC):
    """
    Base class for resources (abstract).

    Subclasses must override:
        - TYPE: the ORM type this resource handles.

    Provides a way to _lookup() resources of its TYPE.
    get(), post(), put(), and delete() endpoint methods to implement the CRUD
    operations for TYPE.
    """

    TYPE: Callable = None

    def _lookup(self, db_, id: int) -> TYPE:
        """lookup the resource by id"""
        try:
            return db_.session.execute(
                db_.select(self.TYPE).filter_by(id=id)
            ).scalar_one()
        except NoResultFound:
            return None

    @db
    def get(self, id: int, *, db_, **kwargs) -> Dict:
        """get the resource"""
        assert not kwargs, f"recieved unhandled {kwargs=}"
        orm = self._lookup(db_, id)
        if not orm:
            return (
                error(f"{self.TYPE.__name__} with id={id} not found"),
                HTTPStatus.NOT_FOUND,
            )
        return orm.asdict()

    @staticmethod
    def _validation_error_response_handler(func):
        """decorator to convert ValidationError into HTTP response"""

        @wraps(func)
        def validation_error_response_handler(*args, **kwargs):
            """
            Convert ValidationError raised by func into HTTP response.
            """
            try:
                return func(*args, **kwargs)
            except ValidationError as ve:
                return ve.json(), HTTPStatus.UNPROCESSABLE_ENTITY

        return validation_error_response_handler

    @_validation_error_response_handler
    @db
    def put(self, id: int, *, db_) -> Dict:
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

        SQLModel/Pydantic validates the fields automatically when the model
        is instantiated, replacing the need for manual field validation.
        """
        j = request.json
        try:
            orm = self._lookup(db_, id)
            if orm is None:
                orm = self.TYPE(**j)  # pylint: disable=not-callable
                orm.id = id
                db_.session.add(orm)
            for attr in orm.asdict().keys():
                if attr in j:
                    setattr(orm, attr, j[attr])
                    del j[attr]
            # raise an error if any attributes can't be processed.
            if j:
                return (error(f"unexpected values: {j}"), HTTPStatus.UNPROCESSABLE_ENTITY)

            db_.session.commit()
            db_.session.refresh(orm)
            return orm.asdict()
        except PydanticValidationError as e:
            return error(str(e)), HTTPStatus.UNPROCESSABLE_ENTITY

    @db
    @_validation_error_response_handler
    def delete(self, id, *, db_):
        """delete the resource"""
        orm = self._lookup(db_, id)
        if orm is not None:
            orm.validate_delete()
            db_.session.delete(orm)
            db_.session.commit()
        return {}


class BaseListResource(Resource):
    """
    Base class for list resources (abstract).

    Subclasses must override:
        - TYPE: the ORM type this resource handles.
    """

    TYPE = None

    @db
    def get(self, *, db_, order_by=None, **filters):
        """get the list of TYPE resources"""
        query = db_.select(self.TYPE)
        if filters:
            query = query.filter_by(**filters)
            if order_by is not None:
                query = query.order_by(order_by)
        return [orm.asdict() for orm in db_.session.execute(query).scalars()]

    @BaseResource._validation_error_response_handler
    @db
    def post(self, db_):
        """create a resource of TYPE"""
        try:
            orm = self.TYPE(**request.json)  # pylint: disable=not-callable
            with db_.session.begin() as session:
                db_.session.add(orm)
                db_.session.flush()
                orm.validate_create_or_update()
            return orm.asdict()
        except PydanticValidationError as e:
            # todo - doesn't appear to be covered by tests.
            return error(str(e)), HTTPStatus.UNPROCESSABLE_ENTITY
        except ValidationError:
            raise  # let decorator handle it
        except IntegrityError as e:
            # todo - we should not be getting IntegrityErrors from the database
            #        since that indicates validation was lacking. But...that's
            #        going to happen, so handle it as a *client* error since
            #        the model is simple enough to make that a good assumption.
            # todo - don't expose internal details (e) to client
            return error(f"{e}"), HTTPStatus.UNPROCESSABLE_ENTITY
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(e)
            # todo - don't expose internal details (e) to client
            return error(f"{e}"), HTTPStatus.INTERNAL_SERVER_ERROR
