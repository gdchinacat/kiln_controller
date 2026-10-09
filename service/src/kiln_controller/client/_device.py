from rest_client import Resource


class Device(Resource):
    _URL = "/device"

    name: str
    user_id: int
    description: str | None = None
