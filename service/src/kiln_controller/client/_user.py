from rest_client import Resource


class User(Resource):
    _URL = "/user"

    name: str
    username: str
    password: str | None = (
        None  # write only for updating user password, not set by service
    )
    email: str | None = None
    phone_number: str | None = None
