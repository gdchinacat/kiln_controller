from datetime import datetime
from flask import request
from flask_restful.utils import unpack
from http import HTTPStatus

from kiln_controller.models import Schedule, Phase
from .base import BaseResource, BaseListResource

def suppress(attr):
    """remove attr from kwargs"""
    def dec(func):
        def wrap(*args, **kwargs):
            kwargs.pop(attr)
            return func(*args, **kwargs)
        return wrap
    return dec

def populate(attr, coerce_func=lambda x: x):
    """populate the attribute from kwargs to request.json"""
    def dec(func):
        def wrap(*args, **kwargs):
            request.json[attr] = coerce_func(kwargs.pop(attr))
            return func(*args, **kwargs)
        return wrap
    return dec

def coerce(attr, is_list, request_coerce, response_coerce):
    def dec(func):
        def wrap(*args, **kwargs):
            if request_coerce:
                request.json[attr] = request_coerce(request.json[attr])
            ret = func(*args, **kwargs)
            (data, code, _) = ret = unpack(ret)
            if code == HTTPStatus.OK and response_coerce:
                if is_list:
                    for item in data:
                        item[attr] = response_coerce(item[attr])
                elif attr in data:
                    data[attr] = response_coerce(data[attr])
            return ret
        return wrap
    return dec

class PhaseResource(BaseResource):
    TYPE = Phase
    
    @suppress('schedule_id')
    @coerce('duration', False, None,
            lambda x: x.isoformat())
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)
    
    @suppress('schedule_id')
    def delete(self, *args, **kwargs):
        print("deleting", args, kwargs)
        return super().delete(*args, **kwargs)

class PhaseListResource(BaseListResource):
    TYPE = Phase
    
    @suppress('schedule_id')
    @coerce('duration', True, None,
            lambda x: x.isoformat())
    def get(self, *args, **kwargs):
        ret = super().get(*args, **kwargs)
        return ret
    
    @populate('schedule_id', int)
    @coerce('duration', False,
            lambda x: datetime.strptime(x, "%H:%M:%S").time(),
            lambda x: x.isoformat())
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)
    
class ScheduleResource(BaseResource):
    TYPE = Schedule
    
class ScheduleListResource(BaseListResource):
    TYPE = Schedule
    