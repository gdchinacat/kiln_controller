'''
Framework for application resources.
'''

from abc import ABC
from dataclasses import MISSING
from functools import wraps
from http import HTTPStatus
from logging import getLogger
from typing import Callable, Dict

from flask import current_app, request
from flask_restful import Resource
from sqlalchemy.exc import NoResultFound, IntegrityError


__all__ = []


logger = getLogger("resource/base.py")


def db(func) -> Callable[[Callable], Callable]:
    '''decorator to inject the database into wrapped calls as db_= kwarg'''
    @wraps(func)
    def wrap(*args, **kwargs):
        db_ = current_app.db  # @UndefinedVariable
        return func(*args, **kwargs, db_=db_)
    return wrap


def error(msg: str) -> Dict[str, str]:
    '''create a json error dict with error msg'''
    # TODO - don't expose internal error messages (500 returns sql error)
    return {"message": msg}


def validate_request_json(func):
    '''
    todo - validate_request_json is deprecated, use marshallers instead
    '''
    @wraps(func)
    def wrap(self: "DataclassFieldJsonValidatorMixin", *args, **kwargs):
        errors = self.validate(request.json)
        if errors:
            return (error(errors),
                    HTTPStatus.UNPROCESSABLE_ENTITY)
        return func(self, *args, **kwargs)
    return wrap


class DataclassFieldJsonValidatorMixin: \
        # pylint: disable=too-few-public-methods
    '''
    validator for json representation of a dataclass

    todo - validate_request_json is deprecated, use marshallers instead
    '''

    TYPE: Callable = None  # class that this is mixed with must provide

    def validate(self, obj_json) -> str:
        '''validate the obj_json dict has the required fields for TYPE'''
        errors = []
        required_fields = {field.name for field in
                           self.TYPE.__dataclass_fields__.values()
                           if (field.init
                               and field.default is MISSING
                               and field.default_factory is MISSING
                               )}
        missing_required = required_fields - set(obj_json)
        if missing_required:
            errors.append("required fields missing: "
                          f"{', '.join(missing_required)}")

        unknown_fields = [x for x in obj_json
                          if x not in self.TYPE.__dataclass_fields__]
        if unknown_fields:
            errors.append(f"unknown fields: {', '.join(unknown_fields)}")

        return "; ".join(errors)


class BaseResource(Resource, DataclassFieldJsonValidatorMixin, ABC):
    '''
    Base class for resources (abstract).

    Subclasses must override:
        - TYPE: the ORM type this resource handles.
        - marshalling data: todo how receive and present the TYPE instances in
                            requests and responses.

    Provides a way to _lookup() resources of its TYPE.
    get(), post(), put(), and delete() endpoing methods to implement the CRUD
    operations for TYPE.

    endpoint methods are decorated with appropriate validation.
    '''
    TYPE: Callable = None

    def _lookup(self, db_, id: int) -> TYPE:
        '''lookup the resource by id'''
        try:
            return db_.session.execute(db_.select(self.TYPE)
                                       .filter_by(id=id)).scalar_one()
        except NoResultFound:
            return None

    @db
    def get(self, id: int, *, db_, **kwargs) -> Dict:
        '''get the resource'''
        assert not kwargs, f"recieved unhandled {kwargs=}"
        orm = self._lookup(db_, id)
        if not orm:
            return (error(f"{self.TYPE.__name__} with id={id} not found"),
                    HTTPStatus.NOT_FOUND)
        return orm.asdict()

    @validate_request_json
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
        """
        j = request.json
        orm = self._lookup(db_, id)
        if orm is None:
            orm = self.TYPE(**j)  # pylint: disable=not-callable
            orm.id = id
            db_.session.add(orm)
        for attr in orm.asdict().keys():  # ('name', 'email', 'phone_number'):
            if attr in j:
                setattr(orm, attr, j[attr])
                del j[attr]
        # raise an error if any attributes can't be processed.
        if j:
            return (error(f"unexpected values: {j}"),
                    HTTPStatus.UNPROCESSABLE_ENTITY)

        db_.session.commit()
        return orm.asdict()

    @db
    def delete(self, id, *, db_):
        '''delete the resource'''
        orm = self._lookup(db_, id)
        if orm is not None:
            db_.session.delete(orm)
            db_.session.commit()
        return {}


class BaseListResource(Resource, DataclassFieldJsonValidatorMixin):
    '''
    Base class for list resources (abstract).

    Subclasses must override:
        - TYPE: the ORM type this resource handles.
        - marshalling data: todo how receive and present the TYPE instances in
                            requests and responses.

    '''
    TYPE = None

    @db
    def get(self, *, db_, order_by=None, **filters):
        '''get the list of TYPE resources'''
        query = db_.select(self.TYPE)
        if filters:
            query = query.filter_by(**filters)
            if order_by is not None:
                query = query.order_by(order_by)
        return [orm.asdict() for orm in
                db_.session.execute(query).scalars()]

    @validate_request_json
    @db
    def post(self, db_):
        '''create a resource of TYPE'''
        try:
            orm = self.TYPE(**request.json)  # pylint: disable=not-callable
            with db_.session.begin() as session:
                session.session.expire_on_commit = False  # don't refresh orm
                db_.session.add(orm)
            return orm.asdict()
        except IntegrityError:
            # todo - implement and use generic IntegrityError handler to
            #        extract the constraint violation and expose it to client
            #        in appropriate manner. For now, just report as client
            #        error.
            return (error("user already exists"),
                    HTTPStatus.UNPROCESSABLE_ENTITY)
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(e)
            # todo - don't expose internal details (e) to client
            return error(f"{e}"), HTTPStatus.INTERNAL_SERVER_ERROR
