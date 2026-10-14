"""
ResoureList et. al. to provide list-like semantics for rest resources.
"""

from collections.abc import Callable, Sequence, Iterable
from dataclasses import dataclass, field, asdict
from functools import wraps
from http import HTTPStatus
import logging
from typing import (
    SupportsIndex,
    Dict,
    Any,
    ClassVar,
    Self,
    override,
    overload,
    Concatenate,
    Protocol,
    Never,
    cast,
    TYPE_CHECKING,
)

import httpx2
import pydantic

from ._resource import Resource, RootResource, _ResourceListDescriptor

if TYPE_CHECKING:
    from ._client import RestClient

logger = logging.getLogger("rest_client")


class ResourceList[T: Resource[Any], PT: Resource[Any]](list[T]):
    """
    List implementation for model elements backing REST resource collections.
    Access is deferred via lazy-refresh upon access (`_unexpire`).

    Generic on T: type of contained resources, PT: parent type
    """

    def __init__(self, type_: type[T], parent: PT):
        self._type = type_
        self._parent = parent
        self._expired = True
        super().__init__()

    @property
    def _url(self) -> str:
        return f"{self._parent._url}{self._type._URL}"

    def expire(self) -> Self:
        """Expire the list, causing it to refresh upon next access."""
        self._expired = True
        super().clear()
        return self

    def refresh(self) -> Self:
        """Populate the list from the remote endpoint."""
        assert self._parent._client
        super().clear()
        for _resource in (
            self._parent._client._http_client.get(self._url).raise_for_status().json()
        ):
            resource = self._type.model_validate(_resource)
            resource._parent = self._parent
            resource._id_reason = Resource.IDReason.DOES_HAVE_AN_ID
            super().append(resource)
        self._expired = False
        return self

    @override
    def clear(self) -> None:
        self.expire()

    @staticmethod
    def _expire[**P, R](
        func: Callable[Concatenate[ResourceList[T, PT], P], R],
    ) -> Callable[Concatenate[ResourceList[T, PT], P], R]:
        @wraps(func)
        def expire_after_call(
            self: ResourceList[T, PT], *args: P.args, **kwargs: P.kwargs
        ) -> R:
            try:
                return func(self, *args, **kwargs)
            finally:
                self.expire()

        return expire_after_call

    @staticmethod
    def _unexpire[**P, R](
        func: Callable[Concatenate[ResourceList[T, PT], P], R],
    ) -> Callable[Concatenate[ResourceList[T, PT], P], R]:
        """
        Decorate a function so that if the ResourceList it is called on is
        expired the list is refreshed before calling the decorated function.
        """

        @wraps(func)
        def _unexpire(
            self: ResourceList[T, PT], *args: P.args, **kwargs: P.kwargs
        ) -> R:
            if self._expired:
                self.refresh()

            return func(self, *args, **kwargs)

        return _unexpire

    # The 'type: ignore[bad-override-mutable-attribute]' are used because type
    # checkers (inconsistently) fail to infer the types properly and complain
    # that this override is incompatible with the base class definitions.
    sort = _unexpire(list.sort)  # type: ignore[bad-override-mutable-attribute]
    index = _unexpire(list.index)  # type: ignore[bad-override-mutable-attribute]
    reverse = _unexpire(list.reverse)  # type: ignore[bad-override-mutable-attribute]
    __contains__ = _unexpire(list.__contains__)  # type: ignore[bad-override-mutable-attribute]
    __eq__ = _unexpire(list.__eq__)  # type: ignore[bad-override-mutable-attribute]
    __getitem__ = _unexpire(list.__getitem__)  # type: ignore[bad-override-mutable-attribute]
    __iter__ = _unexpire(list.__iter__)  # type: ignore[bad-override-mutable-attribute]
    __len__ = _unexpire(list.__len__)  # type: ignore[bad-override-mutable-attribute]

    def _not_implemented(self, *args: Any, **kwargs: Any) -> Callable[..., Never]:
        raise NotImplementedError()

    copy = _not_implemented  # type: ignore[bad-override-mutable-attribute]
    count = _not_implemented  # type: ignore[bad-override-mutable-attribute]
    extend = _not_implemented  # type: ignore[bad-override-mutable-attribute]
    insert = _not_implemented  # type: ignore[bad-override-mutable-attribute]
    pop = _not_implemented  # type: ignore[bad-override-mutable-attribute]
    remove = _not_implemented  # type: ignore[bad-override-mutable-attribute]

    @_expire
    def __iadd__(self, value: Iterable[T]) -> Self:
        assert all(isinstance(obj, self._type) for obj in value), (
            f"all elements in value must be an instance of {self._type}"
            f": {set(type(obj) for obj in value)}"
        )

        for resource in value:
            resource.post(self._parent)
        return self

    def append(self, obj: T) -> None:
        self += (obj,)

    @_expire
    def __delitem__(self, key: SupportsIndex | slice) -> None:
        if isinstance(key, slice):
            for resource in self[key]:
                resource.delete()
        else:
            resource = self[key]
            resource.delete()


class RootResourceList[T: Resource[Any]](ResourceList[T, RootResource]):
    """
    A resource root resrouce lists can use as parent.
    """

    def __init__(self, _type: type[T], client: RestClient):
        super().__init__(_type, parent=RootResource(client))

    @property
    def _url(self) -> str:
        return self._type._URL


class ResourceListDescriptor[T: Resource[Any], PT: Resource[Any]](
    _ResourceListDescriptor[T, PT]
):
    """Descriptor class for dynamic nested resource attributes."""

    type_: type[T]
    name: str
    attr: str

    def __init__(self, type_: type[T]):
        self.type_ = type_

    def __set_name__(self, owner, name):
        self.name = name
        self.attr = f"_{name}"

    def __set__(self, obj: Any, value: ResourceList[T, PT]) -> None:
        setattr(obj, self.attr, value)

    @overload
    def __get__(
        self, parent: PT, parent_type: type[PT] | None = None
    ) -> ResourceList[T, PT]: ...

    @overload
    def __get__(self, parent: None, parent_type: type[PT]) -> Self: ...

    def __get__(
        self, parent: PT | None, parent_type: type[PT] | None = None
    ) -> ResourceList[T, PT] | Self:
        if parent is None:
            return self
        resource_list = cast(ResourceList[T, PT], getattr(parent, self.attr, None))
        if resource_list is None:
            resource_list = ResourceList(
                self.type_,
                parent,
            )
            setattr(parent, self.attr, resource_list)
        return resource_list

    def __repr__(self) -> str:
        return f"ResourceListDescriptor[{self.type_}]"
