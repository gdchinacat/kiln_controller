from kiln_controller.models import Device

from .base import BaseResource, BaseListResource

class DeviceResource(BaseResource):
    TYPE = Device
    
class DeviceListResource(BaseListResource):
    TYPE = Device
    