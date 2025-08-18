from dataclasses import MISSING
from flask_restful import Resource
from flask import current_app, request
from http import HTTPStatus
from sqlalchemy.exc import NoResultFound
from functools import wraps

def db(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        db = current_app.db
        return func(*args, **kwargs, db=db)
    return wrap

def error(msg):
    return {"message": msg}

def validate_request_json(func):
    @wraps(func)
    def wrap(self, *args, **kwargs):
        errors = self.validate(request.json)
        if errors:
                return error(errors), HTTPStatus.UNPROCESSABLE_ENTITY
        else:
            return func(self, *args, **kwargs)
    return wrap

class DataclassFieldJsonValidator:
    """validator for json representation of a dataclass"""
    def validate(self, obj_json):
        errors = []
        required_fields = [field.name for field in self.TYPE.__dataclass_fields__.values()
                           if (    field.init
                               and field.default is MISSING
                               and field.default_factory is MISSING
                               )]
        missing_required = [x for x in required_fields
                            if x not in obj_json]
        if missing_required:
            errors.append(f"required fields missing: {', '.join(missing_required)}")
        
        unknown_fields = [x for x in obj_json if x not in self.TYPE.__dataclass_fields__]
        if unknown_fields:
            errors.append(f"unknown fields: {', '.join(unknown_fields)}")
            
        return "; ".join(errors)
            
class BaseResource(Resource, DataclassFieldJsonValidator):
    TYPE = None
    
    def _lookup(self, db, id):
        try:
            return db.session.execute(db.select(self.TYPE).filter_by(id=id)).scalar_one()
        except NoResultFound:
            return None

    @db
    def get(self, id, *, db, **kwargs):
        orm = self._lookup(db, id)
        if not orm:
            return error(f"{self.TYPE.__name__} with id={id} not found"), HTTPStatus.NOT_FOUND
        return orm.asdict()
    
    @validate_request_json
    @db
    def put(self, id, *, db):
        """
        There is some debate in the REST community as to whether or not clients
        should be allowed to create resources with PUT since it gives the client
        control over what id should be used. If a client decides to use id=1
        and a resource exists with id=1 the service has no way to tell if the
        client intended to create a new entity or update the existing entity,
        so the PUT succeeds, possibly clobbering an entity it didn't intend to
        clobber. However...a naive reading of what PUT should do allows
        resources to be created by id. That is the current implementation.
        
        So, why not just require POST be used? There is no way to idempotently
        create the resource since the client doesn't know how to identify it...
        if the request fails after the resource is created the client doesn't
        know what the id is. The only way to proceed is to retry the POST, which
        may create spurious resources.
        
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
        orm = self._lookup(db, id)
        if orm is None:
            orm = self.TYPE(**j)
            orm.id = id
            db.session.add(orm)
        for attr in orm.asdict().keys():#('name', 'email', 'phone_number'):
            if attr in j:
                setattr(orm, attr, j[attr])
                del j[attr]
        #raise an error if any attributes can't be processed.
        if j:
            return error(f"unexpected values: {j}"), HTTPStatus.UNPROCESSABLE_ENTITY
        
        db.session.commit()
        return orm.asdict()
    
    @db
    def delete(self, id, *, db):
        orm = self._lookup(db, id)
        if orm is not None:
            db.session.delete(orm)
            db.session.commit()
        return {}
    
class BaseListResource(Resource, DataclassFieldJsonValidator):
    TYPE = None
    
    @db
    def get(self, *, db, **filters):
        query = db.select(self.TYPE)
        if filters:
            query = query.filter_by(**filters)
        orms = db.session.execute(query).scalars()
        return [orm.asdict() for orm in orms]
    
    @validate_request_json
    @db
    def post(self, db):
        try:
            orm = self.TYPE(**request.json)
            db.session.add(orm)
            db.session.commit()
        except Exception as e:
            return error(f"{e}"), 500
        return orm.asdict()
    