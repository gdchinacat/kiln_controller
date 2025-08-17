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
from .helpers import logger, detect_bad_url, trace


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
                self.clear()
                self.extend(self.coerce(self._type, self._client.get(self._url)))
        return wrap

    @_refresh
    def __iadd__(self, obj):
        """
        implement the "+=" operator to create a new resource on the server.
        The list is refreshed regardless of success.
        The dictionary representation of obj is used to format() the _url. this
        allows the ids of a parent resource to be placed into the URL. For
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
        return self
    
    def append(self, obj):
        self += obj
        
    @_refresh
    def __delitem__(self, key:SupportsIndex | slice)->None:
        """
        Implement "del list[key|slice]".
        The list is refreshed regardless of success.
        """
        def _del(obj):
            self._client.delete(f"{self._url}/{obj.id}")
        if isinstance(key, slice):
            for obj in self[key]:
                _del(obj)
        else:
            _del(self[key])

    @classmethod
    def coerce(cls, _type, data):
        """
        convert json dicts that represent model elements in resp 
        to instances of _type
        """
        if isinstance(data, list):
            return [_type(**obj) for obj in data]
        else:
            return _type(**data)
    
    @classmethod
    def factory(cls, _type, url):
        """
        Create a method that will create a ResourceList for the specified data model
        _type that is backed by the resources at url (relative to client url).
        """
        def resource_list_factory(self):
            json = self.get(url)
            objs = cls.coerce(_type, json)
            return cls(_type, self, url, objs)
        return resource_list_factory
            
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
    
class Resource(ABC):
    """A resource associates a dataclass with a REST resource"""
    URL: str # format string for the url for this type of resource
        
    @classmethod
    def new(_, cls, url, _attrs={}):
        """Create a new RESTEntity class"""
        attrs = {}
        attrs.update(_attrs)
        attrs['URL'] = url
        #remove last four characters from name to remove Base
        return type(cls.__name__[:-4], (cls, Resource,), attrs)
    
    @classmethod
    def new_child(cls, name, url):
        """Create a child resource of this Resource"""
        child_url = f"{cls.URL}/{{{cls.__name__.lower()}_id}}{url}"
        return cls.new(name, child_url)

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
    
class ClientFactory(BaseRestClient):
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
        locals()[f"{name}s"] = property(ResourceList.factory(resource, url))
        
# make these classes available on the module rather than the client
for (name, cls) in ClientFactory.resource_class_map.items():
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
        self._client = ClientFactory(*args, **kwargs)
        self.refresh()
        
    def refresh(self):
        # copy the top level ResourceLists from the real client.
        self.users = self._client.users
        self.devices = self._client.devices
        self.schedules = self._client.schedules

