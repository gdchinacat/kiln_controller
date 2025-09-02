'''
Application resources for schedule and related objects.
'''

from datetime import datetime
from http import HTTPStatus
import logging
from typing import Dict, Any, Callable

from flask import request
from flask_restful.utils import unpack

from kiln_controller.models import Schedule, Phase

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
           request_coerce: Callable[[Dict], Any],
           response_coerce: Callable[[Dict], Any]):
    """
    The @coerce() decorator is used for translating request and response .json
    attributes using request_coerce() and response_coerce().

    :param attr: name of the json attribute to coerce.
    :param is_list: is the json expected to be a list, with the coercion
                     to be applied to each element of the list.
    :param request_coerce: function to coerce request attributes
    :param response_coerce: function to coerce response attributes
    """
    def dec(func):
        def wrap(*args, **kwargs):
            if request_coerce:
                if request.json.get(attr, None):  # @UndefinedVariable
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
    '''Flask resource for Phases'''
    TYPE = Phase

    # todo - PhaseResource overloads these to add coercion...once
    #        marshallers have been added these overloads should not be
    #        necessary.
    @coerce('duration', False, None,
            lambda x: x.isoformat())
    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def delete(self, *args, schedule_id: int, **kwargs):
        logger.error("PhaseResource ignoring schedule_id=%i path parameter",
                     schedule_id)
        return super().delete(*args, **kwargs)


class PhaseListResource(BaseListResource):
    '''Flask list resource list for Phases'''
    TYPE = Phase

    # todo - PhaseListResource overloads these to add coercion...once
    #        marshallers have been added these overloads should not be
    #        necessary.
    @coerce('duration', True, None,
            lambda x: x.isoformat() if x else None)
    def get(self, *args, **kwargs):
        ret = super().get(*args, **kwargs)
        return ret

    @populate('schedule_id', int)
    @coerce('duration', False,
            lambda x: datetime.strptime(x, "%H:%M:%S").time(),
            lambda x: x.isoformat() if x else None)
    def post(self, *args, **kwargs):
        return super().post(*args, **kwargs)


class ScheduleResource(BaseResource):
    """An individual schedule resource"""
    TYPE = Schedule


class ScheduleListResource(BaseListResource):
    """Resource for a list of schedules"""
    TYPE = Schedule
