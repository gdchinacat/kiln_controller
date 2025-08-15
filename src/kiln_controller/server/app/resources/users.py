from flask_restful import Resource
from flask import current_app, request, render_template
from kiln_controller.models import User
from http import HTTPStatus
from sqlalchemy.exc import NoResultFound

def db(func):
    def wrap(*args, **kwargs):
        db = current_app.db
        return func(*args, **kwargs, db=db)
    return wrap

def error(msg):
    return {"error": msg}

class BaseResource(Resource):
    TYPE = None
    
    def _lookup(self, db, pk):
        try:
            return db.session.execute(db.select(self.TYPE).filter_by(id=pk)).scalar_one()
        except NoResultFound:
            return None

    @db
    def get(self, pk, *, db):
        orm = self._lookup(db, pk)
        if not orm:
            return error(f"{self.TYPE.__name__} with id={pk} not found"), HTTPStatus.NOT_FOUND
        return orm.asdict()
    
    @db
    def put(self, pk, *, db):
        j = request.json
        orm = self._lookup(db, pk)
        if orm is None:
            if 'name' not in j:
                return error("'name' is required"),  HTTPStatus.UNPROCESSABLE_ENTITY
            orm = self.TYPE(j['name'])
            orm.id = pk
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
    def delete(self, pk, *, db):
        orm = self._lookup(db, pk)
        if orm is not None:
            db.session.delete(orm)
            db.session.commit()
        return {}
    
class ListResource(Resource):
    TYPE = None
    
    @db
    def get(self,*, db):
        orms = db.session.execute(db.select(self.TYPE)).scalars()
        return [orm.asdict() for orm in orms]
    
    def post(self):
        orm = self.TYPE(**request.json)
        current_app.db.session.add(orm)
        current_app.db.session.commit()
        return orm.asdict()
    
class UserResource(BaseResource):
    TYPE = User
    
class UserListResource(ListResource):
    TYPE = User