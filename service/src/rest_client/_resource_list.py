"""
ResoureList et. al. to provide list-like semantics for rest resources.
"""

import logging
from collections.abc import Callable, Iterable
from functools import wraps
from typing import (
    TYPE_CHECKING,
    Any,
    Concatenate,
    Never,
    Self,
    SupportsIndex,
    cast,
    overload,
    override,
)

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

    def __init__(self, type_: type[T], parent: PT) -> None:
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
            self._parent._client._http_client.get(self._url)
            .raise_for_status()
            .json()
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

    sort = _unexpire(list.sort)  # type: ignore[missing-override-decorator]
    index = _unexpire(list.index)  # type: ignore[missing-override-decorator]
    reverse = _unexpire(list.reverse)  # type: ignore[missing-override-decorator]
    __contains__ = _unexpire(list.__contains__)  # type: ignore[missing-override-decorator]
    __eq__ = _unexpire(list.__eq__)  # type: ignore[missing-override-decorator]
    __getitem__ = _unexpire(list.__getitem__)  # type: ignore[missing-override-decorator]
    __iter__ = _unexpire(list.__iter__)  # type: ignore[missing-override-decorator]
    __len__ = _unexpire(list.__len__)  # type: ignore[missing-override-decorator]

    def _not_implemented(self, *args: Any, **kwargs: Any) -> Never:
        raise NotImplementedError()

    copy = _not_implemented
    count = _not_implemented
    extend = _not_implemented
    insert = _not_implemented
    pop = _not_implemented
    remove = _not_implemented

    @override
    @_expire
    def __iadd__(self, value: Iterable[T]) -> Self:
        assert all(isinstance(obj, self._type) for obj in value), (
            f"all elements in value must be an instance of {self._type}"
            f": { {type(obj) for obj in value} }"
        )

        for resource in value:
            resource.post(self._parent)
        return self

    @override
    def append(self, obj: T) -> None:
        self += (obj,)

    @override
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

    def __init__(self, _type: type[T], client: RestClient) -> None:
        super().__init__(_type, parent=RootResource(client))

    @property
    @override
    def _url(self) -> str:
        return self._type._URL


class ResourceListDescriptor[T: Resource[Any], PT: Resource[Any]](
    _ResourceListDescriptor[T, PT]
):
    """Descriptor class for dynamic nested resource attributes."""

    type_: type[T]
    name: str
    attr: str

    def __init__(self, type_: type[T]) -> None:
        self.type_ = type_

    def __set_name__(self, owner: Any, name: str) -> None:
        self.name = name
        self.attr = f"_{name}"

    @override
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
        resource_list = cast(
            ResourceList[T, PT], getattr(parent, self.attr, None)
        )
        if resource_list is None:
            resource_list = ResourceList(
                self.type_,
                parent,
            )
            setattr(parent, self.attr, resource_list)
        return resource_list

    def __repr__(self) -> str:
        return f"ResourceListDescriptor[{self.type_}]"
