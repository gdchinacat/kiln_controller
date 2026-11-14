"""
Integration with the metrics backend.

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Protocol

from ...device.protocol import Telemetry

__all__ = ("MetricsServer",)


@dataclass
class QueryResult:
    values: list[tuple[int, int | float | None]]


class UserP(Protocol):
    id: int | None


class FiringP(Protocol):
    id: int | None


class DeviceP(Protocol):
    id: int | None

    @property
    def user(self) -> UserP: ...
    @property
    def firing(self) -> FiringP: ...


class MetricsServer(ABC):
    """
    MetricsServer is an abstraction on top of the underlying time series
    database service the metrics are stored in.
    """

    @abstractmethod
    async def close(self) -> None:
        """
        Close resources.
        """

    @abstractmethod
    async def telemetry(self, telemetry: Telemetry, device: DeviceP) -> int:
        """
        Add the samples from the device to the metric service.

        Returns the last timestamp that was successfully stored.
        """

    @abstractmethod
    async def query(
        self,
        instance: int,
        metric: Literal["uptime", "temperature"],
        start: int | None = None,
        end: int | None = None,
        step: int | None = None,
    ) -> QueryResult:
        """
        Query the metric server for the metrics for the instance within the
        range and given step size.
        """
