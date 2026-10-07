"""
A requests-based client for interacting with the REST server.

Exposes domain-specific resources (User, Device, Schedule, Phase) and high-level
client wrapper interfaces.
"""

import httpx2
from typing import Self
from abc import ABC, abstractmethod


class RestClient(ABC):
    """
    Rest client.
    Basically a wrapper around an http client. Subclasses are expected to place
    their top-level ResourceList here as well.
    """

    _client: httpx2.Client

    def __init__(self, client: httpx2.Client):
        self._client = client

    @abstractmethod
    def expire(self) -> Self:
        """Expire the resource lists exposed by the client."""
        # todo? - use metaclass, __set_name__, etc to do this automatically?
