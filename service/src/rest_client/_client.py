"""
A requests-based client for interacting with the REST server.

Exposes domain-specific resources (User, Device, Schedule, Phase) and high-level
client wrapper interfaces.
"""

from abc import ABC, abstractmethod
from typing import Self, ClassVar, Any, override

import httpx2

from ._resource import RootResource
from ._resource_list import RootResourceList


class RestClient(RootResource, ABC):
    """
    Rest client.
    Basically a wrapper around an http client. Subclasses are expected to place
    their top-level ResourceList here as well.

    Subclasses should look like this:

    class TestClient(RestClient):

        if TYPE_CHECKING:
            # RestClient is a pydantic model for implementation reasons, but
            # the resource lists should not be pydantic fields. However, to
            # make them PrivateAttr to suppress this requires they be prefixed
            # with '_'. If this is not desireable you can hide them from
            # pydantic and still have static type checking by hiding them from
            # pydantic at runtime by putting their declaration in a
            # TYPE_CHECKING guard.
            parents: RootResourceList[Parent]

        def __init__(self, client: httpx2.Client):
            super().__init__(client)
            self.parents = RootResourceList(Parent, self)

        def expire(self) -> Self:
            self.parents.expire()
            return self
    """

    _URL: ClassVar[str] = ""

    __client: httpx2.Client

    def __init__(self, client: httpx2.Client):
        super().__init__(self)
        self.__client = client

    def __setattr__(self, name: str, value: Any) -> None:
        if isinstance(value, RootResourceList):
            # Bypass pydantic for RootResoureLists because they should not be
            # managed by the model. It is convenient for the implementation
            # to make RestClient a Resource which is a pydantic.BaseModel so
            # that is always a parent for actual resources and for the client
            # to be that root resource. However, the client is not a real
            # resource with an actual pydantic model but it inherits it from
            # Resource. When subclasses add their RootResourceList fields
            # pydantic tries to validate the model and is unable to do so
            # because it doesn't know about these fields, so this bypasses it.
            # This helps keep the API for subclasses much cleaner.
            object.__setattr__(self, name, value)
        else:
            super().__setattr__(name, value)

    @abstractmethod
    def expire(self) -> Self:
        """Expire the resource lists exposed by the client."""
        # todo? - use metaclass, __set_name__, etc to do this automatically?

    @override
    @property
    def _url(self) -> str:
        return RestClient._URL

    @override
    @property
    def _client(self) -> RestClient:
        return self

    @property
    def _http_client(self) -> httpx2.Client:
        return self.__client

    @override
    def _testing_shadow(self) -> Self:
        return self
