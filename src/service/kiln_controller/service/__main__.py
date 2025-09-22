'''
The flask application for the kiln_controller service.

Implements the resource model used by the UI and the devices.
'''
import os

from flask import Flask, render_template, current_app
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import configure_mappers

from .models import Base
from .resources import (UserResource, UserListResource,
                        DeviceResource, DeviceListResource,
                        ScheduleResource, ScheduleListResource,
                        PhaseResource, PhaseListResource,
                        )


# debug
#import logging
#logging.basicConfig()
#logging.getLogger('sqlalchemy.engine').setLevel(logging.DEBUG)
# end debug
app = Flask('kiln_controller')
api = Api(app)

# todo - LIVE_SERVICE=true unit tests are much slower if backed by persistent
#        storage. Add the ability for tests to start an app instance that uses
#        a memory backing rather than persistent database.
# app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite://'
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///kiln_controller.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)


@app.route("/")
def default_page():
    return render_template("index.html")


api.add_resource(UserResource, "/user/<string:id>/")
api.add_resource(UserListResource, "/user/")

api.add_resource(DeviceResource, "/device/<string:id>/")
api.add_resource(DeviceListResource, "/device/")

api.add_resource(ScheduleResource, "/schedule/<string:id>/")
api.add_resource(ScheduleListResource, "/schedule/")

api.add_resource(PhaseResource,
                 "/schedule/<string:schedule_id>/phase/<string:id>/")
api.add_resource(PhaseListResource, "/schedule/<string:schedule_id>/phase/")

with app.app_context() as ctx:
    configure_mappers()  # do this proactively rather than when app is started
    db.create_all()
    current_app.db = db

# process environment variables
host = os.getenv('HOST')
port = int(_port) if (_port:=os.getenv('PORT')) else None
debug = _debug.upper() == 'TRUE' if (_debug:=os.getenv('DEBUG')) else False

# run the service
app.run(host=host, port=port, debug=debug)
