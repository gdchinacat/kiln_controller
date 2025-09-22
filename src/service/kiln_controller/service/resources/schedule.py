'''
Application resources for schedule and related objects.
'''

from datetime import datetime
import logging
from typing import Dict, Any, Callable

from flask import request
from flask_restful.utils import unpack

from ...common.enums import PhaseType
from ..models import Schedule, Phase
from .base import BaseResource, BaseListResource


logger = logging.getLogger(__name__)


def populate(attr, coerce_func=lambda x: x):
    """populate the attribute from kwargs to request.json"""
    def dec(func):
        def wrap(*args, **kwargs):
            request.json[attr] = coerce_func(kwargs.pop(attr))
            return func(*args, **kwargs)
        return wrap
    return dec


def coerce(attr: str,
           is_list: bool,
           request_coerce: Callable[[Dict], Any]):
    """
    The @coerce() decorator is used for translating request and response .json
    attributes using request_coerce() and response_coerce().

    :param attr: name of the json attribute to coerce.
    :param is_list: is the json expected to be a list, with the coercion
                     to be applied to each element of the list.
    :param request_coerce: function to coerce request attributes
    """
    def dec(func):
        def wrap(*args, **kwargs):
            if request_coerce:
                if v := request.json.get(attr, None):  # @UndefinedVariable
                    request.json[attr] = request_coerce(v)
            ret = func(*args, **kwargs)
            (data, code, _) = ret = unpack(ret)
            return ret
        return wrap
    return dec


class PhaseResource(BaseResource):
    '''Flask resource for Phases'''
    TYPE = Phase

    def delete(self, *args, schedule_id: int, **kwargs):
        logger.error("PhaseResource ignoring schedule_id=%s path parameter",
                     schedule_id)
        return super().delete(*args, **kwargs)


class PhaseListResource(BaseListResource):
    '''Flask list resource list for Phases'''
    TYPE = Phase

    def get(self, *args, **kwargs):
        '''get the phases, ordered by ordinal'''
        ret = super().get(*args, order_by=Phase.ordinal, **kwargs)
        return ret

    @populate('schedule_id', int)
    @coerce('duration', False,
            lambda x: datetime.strptime(x, "%H:%M:%S").time() if x else None)
    @coerce('phase_type', False,
            lambda x: PhaseType[x])
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)


class ScheduleResource(BaseResource):
    """An individual schedule resource"""
    TYPE = Schedule


class ScheduleListResource(BaseListResource):
    """Resource for a list of schedules"""
    TYPE = Schedule
