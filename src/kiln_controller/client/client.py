"""
A requests based client for interacting with the REST server

It *does not* use the models as those are sqlalchemy mapped and the
client doesn't want any of that. Instead, the objects exposed by the
client are extensions of dict to contain whatever the server emits.
"""
from abc import ABC
import dataclasses
from dataclasses import dataclass, field, asdict
import datetime
from functools import wraps
from typing import SupportsIndex, Set, Any, Sequence
from http import HTTPStatus
import requests
import traceback
from .helpers import logger, detect_bad_url, trace, validate_url
from flask_restful.inputs import url


def format_url(func):
    """
    calculate the url based on the request url, client url, and
    object arguments
    TODO - move this to a method on client
    """
    @wraps(func)
    def wrap(self, url, *args, **kwargs):
        obj = args[0] if args else {}
        url = f"{self.url}{url}/"
        if obj:
            url = url.format(**asdict(obj))
        return func(self, url, *args, **kwargs)
    return wrap
        
class Resource(ABC):
    """A resource associates a dataclass with a REST resource"""
    _URL: str # format string for the url for this type of resource (class)
    _url: str # the url for a specific resource (instance)
    
    _client: "_Client" = None  # associated through _set_client() or get()
        
    @classmethod
    def new(cls, base, url, _attrs={}):
        """Create a new RESTEntity class"""
        attrs = {
            '__init__': Resource.__init__,
            '_URL': url,
            }
        attrs.update(_attrs)
        #remove last four characters from name to remove Base
        name = base.__name__[:-4]
        
        #create a new type that extends both base and cls
        return type(name, (cls, base), attrs)

    @classmethod
    def new_child(cls, name, url):
        """Create a child resource of this Resource"""
        child_url = f"{cls._URL}/{{{cls.__name__.lower()}_id}}{url}"
        return cls.new(name, child_url)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._set_url()
    
    def _update(self, **kwargs):
        """update the resource attributes"""
        # probably a less sketchy way to do this, but it works for now
        super().__init__(**kwargs)
        
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
        def wrap(self, client=None):
            self._client = client or self._client
            if not self._client:
                raise ValueError(f"must associate resources with a client before get'ing them")
            return func(self)
        return wrap
            
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
            raise AttributeError("refusing to POST resource with id (use put()?)")
        # post goes to the Class._URL
        self._update(**self._client._client.post(self._URL, self))

class ResourceList(list):
    """
    List implementation for model elements. Used for REST resource lists.
    Item deletion is intercepted to make REST calls to delete the entity
    on the server.
    """
    def __init__(self, _type, client, url, iterable):
        self._type = _type
        self._client = client
        self._url = url
        super().__init__(iterable)

    def refresh(self):
        """refresh the list of resources"""
        self.clear()
        self.extend(self.coerce(self._client, self._type, self._client.get(self._url)))
        return self

    @staticmethod    
    def _refresh(func):
        """
        Decorator to refresh the resource list after a method may have
        caused it to Change.
        """
        @wraps(func)
        def wrap(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            except Exception as e:
                logger.debug(f"refresh: {func.__name__}({args}, {kwargs} raised:{''.join(traceback.format_exception(e))})")
                raise
            finally:
                self.refresh()
        return wrap

    @_refresh
    def __iadd__(self, obj):
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
        assert isinstance(obj, (self._type)), f"{type(obj)} is not an instance of {self._type}"
        resp = self._client.post(self._url, obj)
        obj.__init__(**resp) # update the object (a bit scary, lets see how this ages)
        obj._set_client(self._client)
        return self
    
    def append(self, obj):
        self += obj
        
    @_refresh
    def __delitem__(self, key:SupportsIndex | slice)->None:
        """
        Implement "del list[key|slice]".
        The list is refreshed regardless of success.
        """
        if isinstance(key, slice):
            for obj in self[key]:
                obj.delete()
        else:
            self[key].delete()

    @classmethod
    def coerce(cls, client, _type, data):
        """
        convert json dicts that represent model elements in resp 
        to instances of _type
        """
        if isinstance(data, list):
            resources = []
            for _data in data:
                resource = _type(**_data)
                resource._set_client(client)
                resources.append(resource)
            return resources
        else:
            resource = _type(**data)
            resource._set_client(client)
            return resource
    
    @classmethod
    def factory(cls, _type, url):
        """
        Create a method that will create a ResourceList for the specified data model
        _type that is backed by the resources at url (relative to client url).
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
        def wrap(*args, **kwargs):
            resp = func(*args, **kwargs)
            if resp.status_code == HTTPStatus.OK:
                resp = resp.json()
                return resp
            else:
                raise Exception(resp.json()['message'])
        return wrap
    
    @detect_bad_url
    @_response_handler
    @format_url
    @trace
    def post(self, url, obj):
        """Post the obj to the url."""
        return requests.post(url, json=asdict(obj))
        
    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def get(self, url):
        """Get a resource or set of resources from url"""
        return requests.get(url)
    
    @detect_bad_url
    @format_url
    @_response_handler
    @trace    
    def delete(self, url):
        """delete a resource at the url"""
        return requests.delete(url)
    
    @detect_bad_url
    @format_url
    @_response_handler
    @trace    
    def put(self, url, obj):
        """delete a resource at the url"""
        return requests.put(url, json=asdict(obj))
    
################################################################################
# The dataclasses for the resource types.
# TODO - move these into model as base classes of the mapped classes?
#        as it stands this duplicates the definitions and isn't very
#        maintainable
################################################################################

def foreign_key(cls, attr):
    """return the type of the referenced cls.attr using annotation"""
    for field in dataclasses.fields(cls):
        if field.name == attr:
            return field.type
    raise ValueError(f"{cls.__name__}.{attr} does not exist")

@dataclass
class DataclassBase(ABC):
    id: int = field(default=None, kw_only=True)     # primary key
    name: str
    
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
    #_user_ids: Sequence[foreign_key(Base, 'id')] = field(default_factory=tuple)
    
@dataclass
class ScheduleBase(DataclassBase):
    ...

@dataclass
class PhaseBase(DataclassBase):
    type: str   # todo enum
    duration: datetime.time
    rate: int
    _schedule_id: foreign_key(ScheduleBase, 'id')
    # todo - add schedule: Schedule (not ScheduleBase)
    
################################################################################
    
class _Client(BaseRestClient):
    """
    _ClientFactory creates Clients, as its name implies.
    """
    resource_class_map = {}
    
    # Expose lists of the top level resources so objects can be accessed.
    for (name, base) in (
            ('user', UserBase),
            ('device', DeviceBase),
            ('schedule', ScheduleBase),
        ):
        #create the resource class
        url = f"/{name}"
        resource = resource_class_map[name.capitalize()] = Resource.new(base, url)
        
        # create a ResourceList
        # This creates an attribute on class that when accessed creates a new
        # ResourceList for the resource at the url.
        locals()[f"{name}s"] = property(ResourceList.factory(resource, url))
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._client = self  # allow resources to be bound to both _Client and Client
        
# make these classes available on the module rather than the client
for (name, cls) in _Client.resource_class_map.items():
    locals()[name] = cls
    

        
class Client:
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

