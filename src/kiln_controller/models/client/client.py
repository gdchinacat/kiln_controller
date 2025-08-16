"""
A requests based client for accessing the model
"""
from abc import ABC
from typing import SupportsIndex
from http import HTTPStatus
import logging
import requests
import traceback

from .. import User, Device, Schedule, Phase
from functools import wraps
from sqlalchemy.sql.functions import func

def noop(*args): ...

logger = logging.getLogger("client")
def enable_client_logging(level=None):
    handler = logging.StreamHandler()
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(level if level is not None else logging.DEBUG)
enable_client_logging(logging.WARNING)
 

def trace(func):
    @wraps(func)
    def wrap(*args, **kwargs):
        logger.debug(f"trace: {func.__name__}({args}, {kwargs})")
        try:
            ret = func(*args, **kwargs)
            logger.debug(f"trace: {func.__name__}({args}, {kwargs} = {ret})")
            return ret
        except Exception as e:
            logger.debug(f"trace: {func.__name__}({args}, {kwargs} raised {''.join(traceback.format_exception(e))})")
            raise e
    return wrap
        
class _List(list):
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
             _List(url="/parent/{parent_id}/child", ...
             ...
             obj = Resource(parent_id=1, ...
             ...
             client.post(url="/parent/1/child", ...
             
        """
        assert isinstance(obj, (self._type))
        self._client.post(self._url, obj)
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
        Create a method that will create a _List for the specified data model
        _type that is backed by the resources at url (relative to client url).
        """
        def resource_list_factory(self):
            json = self.get(url)
            objs = cls.coerce(_type, json)
            return cls(_type, self, url, objs)
        return resource_list_factory
            
            
def detect_bad_url(func):
    """decorator that logs an ERROR when the url is "invalid" """
    @wraps(func)
    def wrap(self, url, *args, **kwargs):
        if url[0] != '/':
            raise ValueError(f"url must begin with '/':{url}")
        
        if any(bad in url for bad in ('{')):
            raise ValueError(f"url contains '{{': {url}")
        return func(self, url, *args, **kwargs)
    return wrap
        
def format_url(func):
    """
    calculate the url based on the request url, client url, and
    object arguments
    """
    @wraps(func)
    def wrap(self, url, *args, **kwargs):
        obj = args[0] if args else {}
        url = f"{self.url}{url}/"
        if obj:
            url = url.format(**obj.asdict())
        return func(self, url, *args, **kwargs)
    return wrap
        
class BaseRestClient(ABC):
    """
    Client to interace with the REST resources.
    Coercion from json to model elements is only performed through the high
    level _List properties. The HTTP methods do not perform coercion.
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
        return requests.post(url, json=obj.asdict())
        
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
    
class Client(BaseRestClient):
    
    for (name, _type, url) in (
        ('users', User, '/user'),
        ('devices', Device, '/device'),
        ('schedules', Schedule, '/schedule'),
        #((Schedule, 'phases'), Phase, '/schedule/{schedule_id}/phase'),
        ):
        prop = property(_List.factory(_type, url))
        prop = prop.setter(noop)
        locals()[name] = prop
        del prop
    
