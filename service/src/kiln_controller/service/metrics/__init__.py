"""
Integration with the metrics backend.

"""

from abc import ABC, abstractmethod

from ...device.protocol import Telemetry
from ..models import DeviceORM

__all__ = ("MetricsServer",)


class MetricsServer(ABC):
    """
    MetricsServer is an abstraction on top of the underlying time series
    database service the metrics are stored in.
    """

    @abstractmethod
    async def telemetry(self, telemetry: Telemetry, device: DeviceORM) -> int:
        """
        Add the samples from the device to the metric service.

        Returns the last timestamp that was successfully stored.
        """
