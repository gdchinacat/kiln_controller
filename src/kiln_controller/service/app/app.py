from flask import Flask, render_template, current_app
from flask_restful import Api
from flask_sqlalchemy import SQLAlchemy
from kiln_controller.models import Base

app = Flask(__name__)
api = Api(app)

app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///kiln_controller.db'
db = SQLAlchemy(model_class=Base)
db.init_app(app)



@app.route("/")
def default_page():
    return render_template("index.html")

from .resources import (UserResource, UserListResource,
                        DeviceResource, DeviceListResource, 
                        ScheduleResource, ScheduleListResource,
                        PhaseResource, PhaseListResource,
                        )
api.add_resource(UserResource, "/user/<string:id>/")
api.add_resource(UserListResource, "/user/")

api.add_resource(DeviceResource, "/device/<string:id>/")
api.add_resource(DeviceListResource, "/device/")

api.add_resource(ScheduleResource, "/schedule/<string:id>/")
api.add_resource(ScheduleListResource, "/schedule/")

api.add_resource(PhaseResource, "/schedule/<string:schedule_id>/phase/<string:id>/")
api.add_resource(PhaseListResource, "/schedule/<string:schedule_id>/phase/")

with app.app_context() as ctx:
    db.create_all()
    current_app.db = db
    
if __name__ == "__main__":
    app.run(debug=True)
        