'''
Framework for application resources.
'''

from abc import ABC
from dataclasses import MISSING, fields as fields
from datetime import datetime
from functools import wraps
from http import HTTPStatus
from logging import getLogger
from typing import Callable, Dict

from flask import current_app, request
from flask_restful import Resource, marshal_with
import flask_restful.fields
from sqlalchemy.exc import NoResultFound

from kiln_controller.client.client import DataclassBase
from sqlalchemy.sql.functions import func


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
        required_fields = [field.name for field in
                           self.TYPE.__dataclass_fields__.values()
                           if (field.init
                               and field.default is MISSING
                               and field.default_factory is MISSING
                               )]
        missing_required = [x for x in required_fields
                            if x not in obj_json]
        if missing_required:
            errors.append("required fields missing: "
                          f"{', '.join(missing_required)}")

        unknown_fields = [x for x in obj_json
                          if x not in self.TYPE.__dataclass_fields__]
        if unknown_fields:
            errors.append(f"unknown fields: {', '.join(unknown_fields)}")

        return "; ".join(errors)


def dc_fields(dc: DataclassBase) -> Dict[str, type]:
    """get mapping of {name: type} for the fields in dc"""
    return {f.name: f.type
            for f in fields(dc)}


def fr_fields(dc_fields_: Dict[str, type]) -> Dict[str, ...]:
    '''translate the python type to flask_restful.fields types'''
    fr_types = {
        int: flask_restful.fields.Integer,
        str: flask_restful.fields.String,
        datetime: flask_restful.fields.DateTime,
        # todo - probably a few more
        }
    return {name: fr_types.get(type_, None)
            for name, type_ in dc_fields_.items()}


class dataclass_marshaller: \
        # pylint: disable=invalid-name, too-few-public-methods
    """
    Decorator that marshals the fields based on the type of resource decorated
    method is handling.

    @dataclass_marshaller
    def get(self, ....):
        ...

    """

    def __call__(self, func):
        @wraps(func)
        def wrap(resource, *args, **kwargs):
            fr_fields_ = fr_fields(dc_fields(fields(resource.TYPE)))
            print(f"{fr_fields_=}")

            return func(resource, *args, **kwargs)
        return wrap


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

    def _lookup(self, db_, id_: int) -> TYPE:
        '''lookup the resource by id_'''
        try:
            return db_.session.execute(db_.select(self.TYPE)
                                       .filter_by(id=id_)).scalar_one()
        except NoResultFound:
            return None

    @dataclass_marshaller()
    @db
    def get(self, id_: int, *, db_, **kwargs) -> Dict:
        '''get the resource'''
        assert not kwargs, f"recieved unhandled {kwargs=}"
        orm = self._lookup(db_, id_)
        if not orm:
            return (error(f"{self.TYPE.__name__} with id={id} not found"),
                    HTTPStatus.NOT_FOUND)
        return orm.asdict()

    @dataclass_marshaller()
    @validate_request_json
    @db
    def put(self, id_: int, *, db_) -> Dict:
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
        orm = self._lookup(db_, id_)
        if orm is None:
            orm = self.TYPE(**j)  # pylint: disable=not-callable
            orm.id = id_
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

    @dataclass_marshaller()
    @db
    def delete(self, id_, *, db_):
        '''delete the resource'''
        orm = self._lookup(db_, id_)
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

    @dataclass_marshaller()
    @db
    def get(self, *, db_, **filters):
        '''get the list of TYPE resources'''
        query = db_.select(self.TYPE)
        if filters:
            query = query.filter_by(**filters)
        orms = db_.session.execute(query).scalars()
        return [orm.asdict() for orm in orms]

    @dataclass_marshaller()
    @validate_request_json
    @db
    def post(self, db_):
        '''create a resource of TYPE'''
        try:
            orm = self.TYPE(**request.json)  # pylint: disable=not-callable
            db_.session.add(orm)
            db_.session.commit()
        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(e)
            return error(f"{e}"), HTTPStatus.INTERNAL_SERVER_ERROR
        return orm.asdict()
