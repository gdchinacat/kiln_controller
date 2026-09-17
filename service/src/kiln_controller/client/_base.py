"""
Base framework and HTTP infrastructure for the REST client.
"""

from abc import ABC
from dataclasses import dataclass, field, asdict
from functools import wraps
from http import HTTPStatus
import logging
from typing import SupportsIndex, Dict, Any, TypeVar, Generic

import requests

from ..common.validators import ValidationError, ValidationErrors
from .helpers import detect_bad_url, trace

logger = logging.getLogger("client")
DEFAULT_TIMEOUT = None


class HTTPStatusException(Exception):
    """Base class for exceptions caused by HTTP status errors."""


class ServerException(HTTPStatusException):
    """Indicates that the client received an HTTP 5xx server error."""


@dataclass
class ClientException(HTTPStatusException):
    """Indicates that the client received an HTTP 4xx client error response."""

    type: str
    msg: str
    input: str


class UnauthorizedException(ClientException):
    """Indicates the client was not authorized to access the resource path (HTTP 401)."""

    def __init__(self, path: str) -> None:
        super().__init__(ValidationErrors.GENERIC.name, "unauthorized", path)


class NotFoundException(ClientException):
    """Indicates the requested resource path was not found (HTTP 404)."""

    def __init__(self, path: str) -> None:
        super().__init__(ValidationErrors.GENERIC.name, "not found", path)


def format_url(func):
    """
    Calculates the full endpoint URL based on the client's base URL and function argument.
    """

    @wraps(func)
    def _format_url(self, url, *args, **kwargs):
        return func(self, f"{self.url}{url}/", *args, **kwargs)

    return _format_url


class Resource(ABC):
    """A resource associates a dataclass with a REST resource."""

    _URL: str  # Format string for the URL path for this resource
    _client: Any = None  # Associated _Client instance
    _parent: "Resource" = None  # The parent resource, None for top-level

    id: int = None

    @classmethod
    def new(cls, base, url, _attrs=None):
        """Dynamically create a concrete REST Resource class combining base dataclass & Resource."""
        attrs = {
            "__init__": Resource.__init__,
            "_URL": url,
        }
        attrs.update(_attrs or {})
        name = base.__name__[:-4] if base.__name__.endswith("Base") else base.__name__

        return type(name, (cls, base), attrs)

    def __init__(self, *args, parent: "Resource" = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._parent = parent

    def _update(self, **kwargs):
        """Update resource state in-place."""
        super().__init__(**kwargs)

    @property
    def _url(self):
        """Compute the relative path for this resource instance."""
        parent_url = self._parent._url if self._parent else ""
        if self.id is not None:
            return f"{parent_url}{self._URL}/{self.id}"
        return f"{parent_url}{self._URL}"

    def _set_client(self, client):
        self._client = client

    @staticmethod
    def _accepts_client(func):
        """Decorator ensuring the resource is associated with a client before performing API operations."""

        @wraps(func)
        def client_injector(self, client=None):
            self._client = client or self._client
            if not self._client:
                raise ValueError(
                    "must associate resources with a client before get'ing them"
                )
            return func(self)

        return client_injector

    @_accepts_client
    def get(self) -> "Resource":
        self._update(**self._client._client.get(self._url))
        return self

    refresh = get

    @_accepts_client
    def delete(self) -> "Resource":
        self._client._client.delete(self._url)
        self.id = None
        return self

    @_accepts_client
    def put(self) -> "Resource":
        self._client._client.put(self._url, self)
        return self

    @_accepts_client
    def post(self) -> "Resource":
        if self.id is not None:
            raise AttributeError("refusing to POST resource with id (use put()?)")
        json = self._client._client.post(self._url, self)
        try:
            self._update(**json)
        except TypeError:
            logger.error(str(json))
            raise
        return self


A = TypeVar("A")


class ResourceList(list, Generic[A]):
    """
    List implementation for model elements backing REST resource collections.
    Access is deferred via lazy-refresh upon access (`_unexpire`).
    """

    def __init__(self, type_, client, url, parent=None, iterable=tuple()):
        self._type = type_
        self._client = client
        self._url = url
        self._parent = parent
        self._expired = True
        super().__init__(iterable)

    def expire(self) -> "ResourceList[A]":
        """Expire the list, causing it to refresh upon next access."""
        self._expired = True
        super().clear()
        return self

    def refresh(self) -> "ResourceList[A]":
        """Populate the list from the remote endpoint."""
        super().clear()
        for data in self._client.get(self._url):
            resource = self._type(parent=self._parent, **data)
            resource._set_client(self._client)
            super().append(resource)
        self._expired = False
        return self

    def clear(self):
        self.expire()

    @staticmethod
    def _expire(func):
        @wraps(func)
        def expire_after_call(self, *args, **kwargs):
            try:
                return func(self, *args, **kwargs)
            finally:
                self.expire()

        return expire_after_call

    @staticmethod
    def _unexpire(func):
        @wraps(func)
        def _unexpire(self, *args, **kwargs):
            if self._expired:
                self.refresh()
            return func(self, *args, **kwargs)

        return _unexpire

    sort = _unexpire(list.sort)
    index = _unexpire(list.index)
    reverse = _unexpire(list.reverse)
    __contains__ = _unexpire(list.__contains__)
    __eq__ = _unexpire(list.__eq__)
    __getitem__ = _unexpire(list.__getitem__)
    __iter__ = _unexpire(list.__iter__)
    __len__ = _unexpire(list.__len__)

    def _not_implemented(self, *args, **kwargs):
        raise NotImplementedError()

    copy = _not_implemented
    count = _not_implemented
    extend = _not_implemented
    insert = _not_implemented
    pop = _not_implemented
    remove = _not_implemented

    @_expire
    def __iadd__(self, obj: A) -> "ResourceList[A]":
        assert isinstance(
            obj, self._type
        ), f"{type(obj)} is not an instance of {self._type}"

        resp = self._client.post(self._url, obj)
        obj.__init__(parent=self._parent, **resp)
        obj._set_client(self._client)
        return self

    def append(self, obj: A):
        self += obj

    @_expire
    def __delitem__(self, key: SupportsIndex | slice) -> None:
        if isinstance(key, slice):
            for resource in self[key]:
                resource.delete()
        else:
            resource = self[key]
            resource.delete()

    @classmethod
    def factory(cls, _type, url):
        def _create_resource_list(client):
            return cls(_type, client, url)

        return _create_resource_list


@dataclass
class DataclassBase(ABC):
    """Base class for remote resource dataclasses."""

    id: int | None = field(default=None, kw_only=True)
    name: str

    concrete_type = None

    def asdict(self) -> Dict[str, Any]:
        return asdict(self)


class ResourceListDescriptor:
    """Descriptor class for dynamic nested resource attributes."""

    type_: DataclassBase = None
    name: str = None
    attr: str = None

    def __init__(self, type_: DataclassBase):
        self.type_ = type_

    def __set_name__(self, owner, name):
        self.name = name
        self.attr = f"_{name}"

    def __set__(self, obj, value):
        setattr(obj, self.attr, value)

    def __get__(self, parent, parent_type=None):
        if parent is None:
            return None

        if not parent._url:
            raise ValueError(
                "subresources require parent to have url (has it been created yet?)"
            )

        resource_list = getattr(parent, self.attr, None)
        if resource_list is None:
            if not parent._client:
                logger.error(f"unable to __get__ {parent=} {self.type_=}")
                return None
            resource_list = ResourceList(
                self.type_.concrete_type,
                parent._client._client,
                f"{parent._url}/{self.name[:-1]}" if parent._url else None,
                parent,
                (),
            )
            setattr(parent, self.attr, resource_list)
        return resource_list

    def __repr__(self) -> str:
        return f"ResourceListDescriptor[{self.type_}]"


class BaseRestClient(ABC):
    """REST resource client framework."""

    def __init__(
        self, username: str, password: str, host: str = "localhost", port: int = 5000
    ) -> None:
        self.auth = (username, password)
        self.url = f"http://{host}:{port}"

    @staticmethod
    def _response_handler(func):
        @wraps(func)
        def response_handler(self, url, *args, **kwargs):
            resp = func(self, url, *args, **kwargs)
            match resp.status_code:
                case HTTPStatus.OK | HTTPStatus.CREATED:
                    return resp.json()
                case HTTPStatus.NO_CONTENT:
                    return None
                case HTTPStatus.UNAUTHORIZED:
                    raise UnauthorizedException(f"{url} {self._client.auth=}")
                case HTTPStatus.NOT_FOUND:
                    raise NotFoundException(url)
                case HTTPStatus.UNPROCESSABLE_ENTITY:
                    json = resp.json()
                    validation_error = ValidationError.from_json(json)
                    if validation_error:
                        raise validation_error

                    error = json["detail"][0]
                    raise ClientException(error["type"], error["msg"], error["input"])
                case server_error if 500 <= server_error <= 599:
                    raise ServerException(str(resp.json()))
                case _:
                    raise ClientException(
                        ValidationErrors.GENERIC.name,
                        str(resp.status_code),
                        str(resp.json()),
                    )

        return response_handler

    @detect_bad_url
    @_response_handler
    @format_url
    @trace
    def post(self, url, obj, timeout=DEFAULT_TIMEOUT):
        obj_dict = obj.asdict()
        del obj_dict["id"]  # todoo is this a hack? It simplifies the client to
        # not have to worry about different types of objects
        # depending on whether it has an ID, an ID less
        # object would have to be add to (ie) /users, and
        # a different would return. The simplifcations the
        # client takes makes this hard. So, just remove the
        # id before sending it to the server. But is there
        # a better way? Practicality beats purity, so there
        # is a todo about it.
        return requests.post(url, json=obj_dict, auth=self.auth, timeout=timeout)

    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def get(self, url, timeout=DEFAULT_TIMEOUT):
        return requests.get(url, auth=self.auth, timeout=timeout)

    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def delete(self, url, timeout=DEFAULT_TIMEOUT):
        return requests.delete(url, auth=self.auth, timeout=timeout)

    @detect_bad_url
    @format_url
    @_response_handler
    @trace
    def put(self, url, obj, timeout=DEFAULT_TIMEOUT):
        return requests.put(url, json=obj.asdict(), auth=self.auth, timeout=timeout)
