"""
Integration with the metrics backend.

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, Protocol

from ...device.protocol import Telemetry

__all__ = ("MetricsServer",)


@dataclass
class Series:
    metric: str
    values: list[int | float | None]


@dataclass
class QueryResult:
    times: list[datetime]
    series: list[Series]


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
        metrics: list[Literal["uptime", "temperature"]],
        start: datetime | None = None,
        end: datetime | None = None,
        step: int | None = None,
    ) -> QueryResult:
        """
        Query the metric server for the metrics for the instance within the
        range and given step size.
        """
