"""
REST client framework.
"""

from abc import ABC
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field, asdict
from functools import wraps
from http import HTTPStatus
import httpx2
import logging
from typing import SupportsIndex, Dict, Any, ClassVar, Self

import pydantic
import requests

from ..common.validators import ValidationError, ValidationErrors
from .helpers import detect_bad_url, trace

logger = logging.getLogger("client")
DEFAULT_TIMEOUT = None


class ResourceList[T](list[T]):
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
