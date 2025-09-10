# The current implementation relies heavily on accessing "protected" members
# pylint: disable=protected-access
"""
A requests based client for interacting with the REST server

It *does not* use the models as those are sqlalchemy mapped and the
client doesn't want any of that. Instead, the objects exposed by the
client are extensions of dict to contain whatever the server emits.

TODO - this should be rewritten using metaclasses rather than the trickery
it currently involves. For example, client methods are defined in the factory
method rather than on the classes themselves. I believe proper use of
metaclasses will alleviate this problem.
"""

from abc import ABC
from dataclasses import dataclass, field, asdict
import dataclasses
import datetime
from functools import wraps, partial
from http import HTTPStatus
import traceback
from typing import SupportsIndex, Callable

import requests

from .helpers import logger, detect_bad_url, trace, validate_url

DEFAULT_TIMEOUT = 5


class ClientException(Exception):
    """Used to indicate the client received an error http response"""


def format_url(func):
    """
    calculate the url based on the request url, client url, and
    object arguments
    TODO - move this to a method on client
    """
    @wraps(func)
    def _format_url(self, url, *args, **kwargs):
        # obj = args[0] if args else {}
        url = f"{self.url}{url}/"
        # if obj:
        #     url = url.format(**asdict(obj))
        return func(self, url, *args, **kwargs)
    return _format_url


class Resource(ABC):
    """A resource associates a dataclass with a REST resource"""
    _URL: str  # format string for the url for this type of resource (class)
    _url: str  # the url for a specific resource (instance)

    _client: "_Client" = None  # associated through _set_client() or get()

    id: int = None
    """the id for the resource"""

    @classmethod
    def new(cls, base, url, _attrs=None):
        """Create a new RESTEntity class"""
        attrs = {
            '__init__': Resource.__init__,
            '_URL': url,
            }
        attrs.update(_attrs or {})
        # remove last four characters from name to remove Base
        name = base.__name__[:-4]

        # create a new type that extends both base and cls
        return type(name, (cls, base), attrs)

    @classmethod
    def new_child(cls, name, url):
        """Create a child resource of this Resource"""
        child_url = f"{cls._URL}/{{{cls.__name__.lower()}_id}}{url}"
        return cls.new(name, child_url)

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._set_url()

    def _update(self, **kwargs):
        """update the resource attributes"""
        # probably a less sketchy way to do this, but it works for now
        super().__init__(**kwargs)
        self._set_url()

    def _set_url(self):
        if self.id is not None:
            url = f"{self._URL}/{self.id}"
            validate_url(url)
            self._url = url
        else:
            self._url = None

    def _set_client(self, client):
        # this is separate from __init__ so that Resources can be created
        # without specifying their client, and are associated with the client
        # only once added to a list or refreshed.
        self._client = client

    @staticmethod
    def _requires_url(func):
        """decorator to populate the _url if possible"""
        @wraps(func)
        def wrap(self, *args, **kwargs):
            self._set_url()
            if not self._url:
                raise ValueError(f"{self} has no _url (no id)")
            return func(self, *args, **kwargs)
        return wrap

    @staticmethod
    def _accepts_client(func):
        """
        decorator to allow decorated function to take a client kwarg to
        associate the resource with the client.
        The only reason to accept client is because it is requred, this also
        validates a client exists on self.
        If specified, the clientl is *NOT* passed to the decorated method.
        """
        @wraps(func)
        def client_injector(self, client=None):
            self._client = client or self._client \
              # pylint: disable=protected-access
            if not self._client:  # pylint: disable=protected-access
                raise ValueError("must associate resources with a client "
                                 "before get'ing them")
            return func(self)
        return client_injector

    @_accepts_client
    @_requires_url
    def get(self):
        self._update(**self._client._client.get(self._url))
        return self

    @_accepts_client
    @_requires_url
    def delete(self):
        self._client._client.delete(self._url)
        self.id = None
        # TODO - if this resource came from a ResourceList refresh the list?

    @_accepts_client
    @_requires_url
    def put(self):
        self._client._client.put(self._url, self)

    @_accepts_client
    def post(self):
        if self.id is not None:
            raise AttributeError(
                "refusing to POST resource with id (use put()?)")
        # post goes to the Class._URL
        self._update(**self._client._client.post(self._URL, self))


class ResourceList[A](list):
    """
    List implementation for model elements. Used for REST resource lists.
    Item deletion is intercepted to make REST calls to delete the entity
    on the server.
    """
    def __init__(self, _type, client, url, iterable=tuple()):
        self._type = _type
        self._client = client
        self._url = url
        super().__init__(iterable)

    def refresh(self):
        """refresh the list of resources"""
        self.clear()
        self.extend(self.coerce(self._client, self._type,
                                self._client.get(self._url)))
        return self

    @staticmethod
    def _refresh(func):
        """
        Decorator to refresh the resource list after a method may have
        caused it to Change.
        """
        @wraps(func)
        def refresh_after_call(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.debug(  # pylint: disable=logging-fstring-interpolation
                    f"refresh: {func.__name__}({args}, {kwargs} "
                    f"raised:{''.join(traceback.format_exception(e))})")
                raise
            finally:
                self.refresh()
        return refresh_after_call

    @_refresh
    def __iadd__(self, obj: A) -> A:
        """
        implement the "+=" operator to create a new resource on the server.
        The list is refreshed regardless of success.
        The dictionary representation of obj is used to format() the _url. this
        allows the ids of a parent resource to be placed into the url. For
        example:
             ResourceList(url="/parent/{parent_id}/child", ...
             ...
             obj = Resource(parent_id=1, ...
             ...
             client.post(url="/parent/1/child", ...
        """
        assert isinstance(obj, (self._type)), \
            f"{type(obj)} is not an instance of {self._type}"
        resp = self._client.post(self._url, obj)

        # update the object (a bit scary, lets see how this ages)
        obj.__init__(**resp)
        obj._set_client(self._client)

        return self

    def append(self, obj: A):
        self += obj

    @_refresh
    def __delitem__(self, key: SupportsIndex | slice) -> None:
        """
        Implement "del list[key|slice]".
        The list is refreshed regardless of success.
        """
        if isinstance(key, slice):
            for resource in self[key]:
                resource.delete()
        else:
            resource = self[key]
            resource.delete()

    @classmethod
    def coerce(cls, client, _type, data):
        """
        convert json dicts that represent model elements in resp to instances
        of _type
        """
        if isinstance(data, list):
            # todo - move list handling to different decorator (list_coerce?)
            resources = []
            for _data in data:
                resource = _type(**_data)
                resource._set_client(client)
                resources.append(resource)
            return resources

        resource = _type(**data)
        resource._set_client(client)
        return resource

    @classmethod
    def factory(cls, _type, url):
        """
        Create a method that will create a ResourceList for the specified data
        model _type that is backed by the resources at url (relative to client
        url).
        """
        def _create_resource_list(client):
            # this class effectively becomes a method on Client
            data = client.get(url)
            resources = cls.coerce(client, _type, data)
            return cls(_type, client, url, resources)
        return _create_resource_list


class BaseRestClient(ABC):
    """
    Client to interace with the REST resources.
    Coercion from json to model elements is only performed through the high
    level ResourceList properties. The HTTP methods do not perform coercion.
    TODO - refactor into ABCClient to decouple it from the model it supports.
    """
    def __init__(self, host='localhost', port=5000):
        self.url = f"http://{host}:{port}"

    @staticmethod
    def _response_handler(func):
        """
        Inspect the response of HTTP requests.
        If the response status is 200 OK return the json. Otherwise, raise an
        Exception using the 'message' field in the response json.
        TODO - make this more robust so it doesn't replace errors with its own
        errors from mishandling unexpected response formats (ie the response
        is not json).
        """
        @wraps(func)
        def response_handler(*args, **kwargs):
            resp = func(*args, **kwargs)
            if resp.status_code == HTTPStatus.OK:
                return resp.json()
            raise ClientException(resp.json()['message'])
        return response_handler

    @detect_bad_url
    @_response_handler
    @format_url
    @trace
    def post(self, url, obj, timeout=DEFAULT_TIMEOUT):
        """Post the obj to the url."""
        return requests.post(url, json=obj.asdict(), timeout=timeout)

    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def get(self, url, timeout=DEFAULT_TIMEOUT):
        """Get a resource or set of resources from url"""
        return requests.get(url, timeout=timeout)

    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def delete(self, url, timeout=DEFAULT_TIMEOUT):
        """delete a resource at the url"""
        return requests.delete(url, timeout=timeout)

    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def put(self, url, obj, timeout=DEFAULT_TIMEOUT):
        """delete a resource at the url"""
        return requests.put(url, json=obj.asdict(), timeout=timeout)

###############################################################################
# The dataclasses for the resource types.
# TODO - move these into model as base classes of the mapped classes?
#        as it stands this duplicates the definitions and isn't very
#        maintainable
###############################################################################


@dataclass
class DataclassBase(ABC):
    """
    Base class for remote resource dataclasses.
    Contains the common attributes all model elements share:
      id - the primary key for the model instance (unique by mapped table)
      name - the primary key for the model instance (unique by mapped table)
    """
    id: int = field(default=None, kw_only=True)     # primary key
    name: str

    concrete_type = None
    '''
    filled out when the concrete types are created, used by
    ResourceListDescriptor
    '''

    def asdict(self):
        '''
        Get the json representation.
        Defaults to using dataclasses.asdict, subclasses may override
        '''
        return asdict(self)


@dataclass
class UserBase(DataclassBase):
    email: str = None
    phone_number: str = None


@dataclass
class DeviceBase(DataclassBase):
    host: str
    port: int
    url: str = "/"
    description: str = None


@dataclass
class PhaseBase(DataclassBase):
    type: str   # todo enum
    duration: datetime.time
    rate: int

    _schedule_id: int | None = None
    schedule: 'Schedule' = None


class ResourceListDescriptor:
    '''
    Descriptor class for dataclass fields that are resource lists.

    This is necessary since field(default_factory=) takes a zero arg callable
    and the creation of the ResourceList requires the containing resource to
    scope the ResourceList properly (through the containing resource's url.
    '''
    type_: DataclassBase = None
    attr: str = None

    def __init__(self, type_: DataclassBase):
        self.type_ = type_

    def __set_name__(self, owner, name):
        self.attr = "_" + name

    def __set__(self, obj, value):
        setattr(obj, self.attr, value)

    def __get__(self, parent, parent_type=None):
        '''
        Creates the ResourceList for self.type_ resources for parent.
        The resource list is set on parent so subsequent accesses do not use
        this descriptor.
        '''
        if parent is None:  # class attribute access
            return None

        if not parent._url:
            raise ValueError("subresources require parent to have url"
                             " (has it been created yet?)")

        resource_list = getattr(parent, self.attr, None)
        if resource_list is None:
            resource_list = ResourceList(self.type_.concrete_type,
                                         parent._client._client,
                                         f"{parent._url}/phase"
                                         if parent._url else None,
                                         ())
            setattr(parent, self.attr, resource_list)
        return resource_list


@dataclass
class ScheduleBase(DataclassBase):

    phases: ResourceList['Phase'] = ResourceListDescriptor(PhaseBase)

    def asdict(self):
        return {'id': self.id,
                'name': self.name}

###############################################################################


class _Client(BaseRestClient):
    """
    _ClientFactory creates Clients, as its name implies.
    """
    resource_class_map = {}

    users: ResourceList["Device"]
    devices: ResourceList["User"]
    schedules: ResourceList["Schedule"]

    # Expose lists of the top level resources so objects can be accessed.
    for (name, base) in (
            ('user', UserBase),
            ('device', DeviceBase),
            ('schedule', ScheduleBase),
            ('phase', PhaseBase),
            ):
        # create the resource class
        url = f"/{name}"
        resource = Resource.new(base, url)
        base.concrete_type = resource
        resource_class_map[name.capitalize()] = resource

        # create a ResourceList
        # This creates an attribute on class that when accessed creates a new
        # ResourceList for the resource at the url.
        locals()[f"{name}s"] = property(ResourceList.factory(resource, url))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # allow resources to be bound to both _Client and Client
        self._client = self


# make linters happy (overridden below)
User: Callable = None
Device: Callable = None
Schedule: Callable = None
Phase: Callable = None


# copy these classes to the module from the client
_name, _cls = None, None
for (_name, _cls) in _Client.resource_class_map.items():
    locals()[_name] = _cls
del _name, _cls  # cleanup to silence pylint errors


class Client:  # pylint: disable=too-few-public-methods
    """
    The kiln_controller client interface.

    Client provides a view of the top-level resources as resource lists.
    """
    users: ResourceList
    devices: ResourceList
    schedules: ResourceList

    def __init__(self, *args, **kwargs):
        self._client = _Client(*args, **kwargs)
        self.refresh()

    def refresh(self):
        # copy the top level ResourceLists from the real client.
        self.users = self._client.users
        self.devices = self._client.devices
        self.schedules = self._client.schedules
