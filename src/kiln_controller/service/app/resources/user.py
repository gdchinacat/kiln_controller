from kiln_controller.service.models import User

from .base import BaseResource, BaseListResource


class UserResource(BaseResource):
    TYPE = User


class UserListResource(BaseListResource):
    TYPE = User
