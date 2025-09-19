'''
User resource implementation.
'''
from ....common import ValidationError, ValidationErrors
from ...models import User
from .base import BaseResource, BaseListResource


class UserResource(BaseResource):
    TYPE = User

    def _validate_delete(self, user: BaseResource):
        super()._validate_delete(user)

        if user.schedules:
            raise ValidationError(ValidationErrors.USER_HAS_SCHEDULES)
        #if user.devices.has():
        #    raise ValidationError(ValidationErrors.USER_HAS_SCHEDULES)


class UserListResource(BaseListResource):
    TYPE = User
