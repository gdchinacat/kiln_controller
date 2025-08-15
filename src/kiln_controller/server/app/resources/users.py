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

class UserResource(Resource):
    
    def _lookup(self, db, pk):
        try:
            return db.session.execute(db.select(User).filter_by(id=pk)).scalar_one()
        except NoResultFound:
            return None
    @db
    def get(self, pk, *, db):
        user = self._lookup(db, pk)
        if not user:
            return error(f"user with id={pk} not found"), HTTPStatus.NOT_FOUND
        return user.asdict()
    
    @db
    def put(self, pk, *, db):
        j = request.json
        user = self._lookup(db, pk)
        if user is None:
            if 'name' not in j:
                return error("'name' is required"),  HTTPStatus.UNPROCESSABLE_ENTITY
            user = User(j['name'])
            user.id = pk
            db.session.add(user)
        for attr in user.asdict().keys():#('name', 'email', 'phone_number'):
            if attr in j:
                setattr(user,attr, j[attr])
                del j[attr]
        #raise an error if any attributes can't be processed.
        if j:
            return error(f"unexpected values: {j}"), HTTPStatus.UNPROCESSABLE_ENTITY
        
        current_app.db.session.commit()
        return user.asdict()
    
    @db
    def delete(self, pk, *, db):
        user = self._lookup(db, pk)
        if user is not None:
            db.session.delete(user)
            db.session.commit()
        return {}
    
class UserListResource(Resource):
    @db
    def get(self,*, db):
        users = db.session.execute(db.select(User)).scalars()
        return [user.asdict() for user in users]
    
    def post(self):
        user = User(**request.json)
        current_app.db.session.add(user)
        current_app.db.session.commit()
        return user.asdict()