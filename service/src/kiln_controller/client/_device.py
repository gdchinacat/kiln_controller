from rest_client import Resource, RestClient


class Device(Resource[RestClient]):
    _URL = "/device"

    name: str
    user_id: int
    description: str | None = None
    auth_token: str | None = None  # only exists on responses to POST
