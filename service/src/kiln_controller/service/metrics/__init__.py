"""
Integration with the metrics backend.

"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal, Protocol

from ...device.protocol import Telemetry
from ..models.metrics import METRICS_INFO, MetricsInfo

__all__ = ("MetricsServer",)

type MetricName = Literal[
    "telemetry",
    "telemetry_state",
    "sample_count",
    "time_delta",
    "uptime",
    "state",
    "temperature",
    "temperature.core",
    "temperature.target",
    "temperature.cold_junction",
    "memory.size",
    "memory.heap_free",
    "memory.min_heap_free",
    "memory.largest_allocatable",
    "memory.sample_buffer_size",
    "duty_cycle",
    "sub_sample_count",
]


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

    @property
    def supported_metrics(self) -> MetricsInfo:
        """Get the metrics the server provides."""
        return METRICS_INFO

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
        metric: MetricName,
        start: int | str | None = None,
        end: int | str | None = None,
        step: int | str | None = None,
    ) -> QueryResult:
        """
        Query the metric server for the metrics for the instance within the
        range and given step size.
        """
