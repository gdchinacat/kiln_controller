"""
REST client framework.
"""

from abc import ABC
from collections.abc import Callable, Iterable
from enum import Enum
from functools import wraps
import functools
import logging
from typing import Any, ClassVar, Self, Concatenate, TYPE_CHECKING

import httpx2
import pydantic

if TYPE_CHECKING:
    from ._client import RestClient
    from ._resource_list import ResourceList

logger = logging.getLogger("client.rest_client")


class _ResourceListDescriptor[T: Resource[Any], PT: Resource[Any]]:
    def __set__(self, obj: Any, value: ResourceList[T, PT]): ...


class Resource[PT: "Resource[Any]"](pydantic.BaseModel, ABC):
    """
    Resource is the base class for REST resources.

    Each resource has a URL format string that is concatentated to the parent
    url (or "") to create the url for the specific resource instance (does not
    include the server portion of the url).

    All resources have an ID which may be None when the resource has not yet
    been created.

    Generic on PT (Parent Type).
    """

    model_config = pydantic.ConfigDict(
        validate_assignment=True,
        ignored_types=(_ResourceListDescriptor,),
    )

    _URL: ClassVar[str]
    """
    The path that is appended to the parent (PT) URL to construct the base URL
    for the resource type (what is POST'ed to to). The HTTP REST methods build
    the instance URL for the request type.
    """

    _parent: PT | None = pydantic.PrivateAttr(None)
    """
    The parent resource. Used for building the resource url and accessing a
    client. This can be None when the resource has not yet been associated with
    an existing resource or client (typically through a ResourceList
    attribute).
    """

    id: int | None = None
    """The ID of the resource. Can be None when the resource is pending or
    deleted."""

    class IDReason(str, Enum):
        NOT_YET_CREATED = "has not yet been created"
        DOES_HAVE_AN_ID = "does have an id"
        HAS_BEEN_DELETED = "has been deleted"

    _id_reason: IDReason = pydantic.PrivateAttr(IDReason.NOT_YET_CREATED)

    def __init__(
        self,
        parent: PT | None = None,
        *args: Any,
        **kwargs: Any,
    ):
        """
        Create a resource.
        parent: optional parent resource (None when creating a pending
                resource, not None when accessed through the parent resource).
        """
        super().__init__(*args, **kwargs)
        self._parent = parent

    def __setattr__(self, name: str, value: Any) -> None:
        """work around pydantic descriptor issues (allow += on ResourceListDescriptor"""
        descriptor = getattr(type(self), name, None)

        if isinstance(descriptor, _ResourceListDescriptor):
            descriptor.__set__(self, value)
        else:
            super().__setattr__(name, value)

    @property
    def _client(self) -> "RestClient":
        """
        The client to use to make requests for this resource. The client is
        actually established through a recursive parent chain to a root
        'resource' that provides the client. This ensures the full url path
        to the resource exists when a client is requested for it.
        """
        assert self._parent, """resource must be attached to a parent to get a client"""
        return self._parent._client

    @property
    def _url(self) -> str:
        """
        Compute the path for this resource instance (excluding the client base_url.

        The URL for a resource is calculated from the parents, so make sure
        this resource has a parent. Resources are typically created without
        a parent and then associated when appended to another resources or
        clients ResourceList (ie client.users, or schedule.phases). When the
        resource is retrieved from the service the parent is known and set.

        In addition to needing a parent to build the URL the parent must have
        an unbroken chain of parents to the RootResource that exists to end
        the recursion, ensure all attached resources have a parent, and to
        provide the client with the server portion of the url.

        Lastly, a resoure identifies a specific enntity and needs an id.
        """
        assert self._parent, "detached resources do not have a url"
        assert (
            self._client is not None
        ), "resources that have no client do not have a url"
        assert self.id is not None, f"{self!r} has no id, it {self._id_reason.value}"

        return f"{self._parent._url}{self._URL}/{self.id}"

    @classmethod
    def from_response(cls, response: httpx2.Response, parent: PT) -> Self:
        """Create a resource from an response and parent resource."""
        resource = cls.model_validate(response.raise_for_status().json())
        resource._id_reason = cls.IDReason.DOES_HAVE_AN_ID
        resource._parent = parent
        return resource

    def _update(
        self,
        response: httpx2.Response,
        parent: PT | None = None,
    ) -> None:
        """
        Update the resource based on the http application/json response.
        Resources are typically associated with the parent to calculate the url
        so it is notable that this method can also update the parent. This
        supports the ResourceList use case where the resource is accessed
        through a parents url and the resulting resource objects (self in this
        context) need to be associated with the parent. This association does
        not strictly need to be made in this method, it does not need it to
        update the resource from the response json, but it is a convenient
        place to put it because it is always paired with the data update.
        """
        response.raise_for_status()
        if parent:
            self._parent = parent
        for k, v in response.json().items():
            setattr(self, k, v)
            if k == "id" and v is not None:
                self._id_reason = self.IDReason.DOES_HAVE_AN_ID

    def get(self, parent: PT | None = None) -> Self:
        if parent:
            self._parent = parent
        assert self._client  # LBYL to make type checker happy
        self._update(self._client._http_client.get(self._url))
        return self

    refresh = get

    def delete(self, parent: PT | None = None) -> Self:
        if parent:
            self._parent = parent
        assert self._client  # LBYL to make type checker happy
        self._client._http_client.delete(self._url).raise_for_status()
        self.id = None
        self._id_reason = self.IDReason.HAS_BEEN_DELETED
        return self

    def put(self, parent: PT | None = None) -> Self:
        if parent:
            self._parent = parent
        assert self._client  # LBYL to make type checker happy
        self._update(
            self._client._http_client.put(self._url, json=self.model_dump(mode="json"))
        )
        return self

    def post(self, parent: PT | None = None) -> Self:
        if parent:
            self._parent = parent
        if self.id is not None:
            raise AttributeError("refusing to POST resource with id (use put()?)")
        assert self._parent
        assert self._client
        self._update(
            self._client._http_client.post(
                f"{self._parent._url}{self._URL}",
                json=self.model_dump(mode="json"),
            )
        )
        return self

    def _testing_shadow(self) -> Self:
        assert self._parent
        _parent = self._parent._testing_shadow()
        clone = type(self).model_validate(self.model_dump())
        return clone.get(_parent)


class RootResource(Resource["RestClient"]):

    def __init__(self, client: "RestClient"):
        super().__init__()  # root resources are internal and don't have args
        self.__client = client

    @property
    def _client(self) -> "RestClient":
        return self.__client

    @property
    def _url(self) -> str:
        return ""
