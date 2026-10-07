"""
REST client framework.
"""

from abc import ABC
from collections.abc import Callable
from functools import wraps
import logging
from typing import Any, ClassVar, Self

import httpx2
import pydantic
import functools

logger = logging.getLogger("client.rest_client")


class Resource[PT: Resource[Any, Any], **P](pydantic.BaseModel, ABC):
    """
    Resource is the base class for REST resources.

    Each resource has a URL format string that is concatentated to the parent
    url (or "") to create the url for the specific resource instance (does not
    include the server portion of the url).

    All resources have an ID which may be None when the resource has not yet
    been created.
    """

    model_config = pydantic.ConfigDict(validate_assignment=True)

    _URL: ClassVar[str]
    """Format string for the URL path for this resource."""

    _client: httpx2.Client | None = pydantic.PrivateAttr()
    """
    The client to use to communicate with the service.
    May be none for resources that have not yet been attached to a client.
    """

    _parent: PT | None = pydantic.PrivateAttr()
    id: int | None = None

    def __init__(
        self,
        parent: PT | None = None,
        client: httpx2.Client | None = None,
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._parent = parent
        self._client = client

    @property
    def _url(self) -> str:
        """
        Compute the path for this resource instance (excluding the client base_url.
        """
        parent_url = self._parent._url if self._parent else ""
        assert self.id is not None, "resources that have no ID do not have a url"
        return f"{parent_url}{self._URL}/{self.id}"

    def _update(self, response: httpx2.Response) -> None:
        response.raise_for_status()
        for k, v in response.json().items():
            setattr(self, k, v)

    def get(self, client: httpx2.Client | None = None) -> Self:
        self._client = client or self._client
        assert self._client  # LBYL to make type checker happy
        self._update(self._client.get(self._url))
        return self

    refresh = get

    def delete(self, client: httpx2.Client | None = None) -> Self:
        self._client = client or self._client
        assert self._client  # LBYL to make type checker happy
        self._client.delete(self._url).raise_for_status()
        self.id = None
        return self

    def put(self, client: httpx2.Client | None = None) -> Self:
        self._client = client or self._client
        assert self._client  # LBYL to make type checker happy
        self._update(self._client.put(self._url, json=self.model_dump()))
        return self

    def post(self, client: httpx2.Client | None = None) -> Self:
        if self.id is not None:
            raise AttributeError("refusing to POST resource with id (use put()?)")
        self._client = client or self._client
        assert self._client  # LBYL to make type checker happy
        self._update(
            self._client.post(
                f"{self._parent._URL if self._parent else ''}{self._URL}",
                json=self.model_dump(),
            )
        )
        return self
