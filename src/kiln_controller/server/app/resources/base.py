from dataclasses import MISSING
from flask_restful import Resource
from flask import current_app, request
from http import HTTPStatus
from sqlalchemy.exc import NoResultFound

def db(func):
    def wrap(*args, **kwargs):
        db = current_app.db
        return func(*args, **kwargs, db=db)
    return wrap

def error(msg):
    return {"message": msg}

def validate_request_json(func):
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
    def get(self, id, *, db):
        orm = self._lookup(db, id)
        if not orm:
            return error(f"{self.TYPE.__name__} with id={id} not found"), HTTPStatus.NOT_FOUND
        return orm.asdict()
    
    @validate_request_json
    @db
    def put(self, id, *, db):
        j = request.json
        orm = self._lookup(db, id)
        if orm is None:
            if 'name' not in j:
                return error("'name' is required"),  HTTPStatus.UNPROCESSABLE_ENTITY
            orm = self.TYPE(j['name'])
            orm.id = id
            db.session.add(orm)
        for attr in orm.asdict().keys():#('name', 'email', 'phone_number'):
            if attr in j:
                setattr(orm, attr, j[attr])
                del j[attr]
        #raise an error if any attributes can't be processed.
        if j:
            return error(f"unexpected values: {j}"), HTTPStatus.UNPROCESSABLE_ENTITY
        
        current_app.db.session.commit()
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
    def get(self,*, db):
        orms = db.session.execute(db.select(self.TYPE)).scalars()
        return [orm.asdict() for orm in orms]
    
    @validate_request_json
    def post(self):
        try:
            orm = self.TYPE(**request.json)
            current_app.db.session.add(orm)
            current_app.db.session.commit()
        except Exception as e:
            return error(f"{e}"), 500
        return orm.asdict()
    