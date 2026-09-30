"""
Integration with the metrics backend.

"""

from abc import ABC, abstractmethod

from ...device.protocol import Telemetry
from ..models import DeviceORM


class MetricsServer(ABC):
    """
    MetricsServer is an abstraction on top of the underlying time series
    database service the metrics are stored in.
    """

    @abstractmethod
    async def telemetry(self, telemetry: Telemetry, device: DeviceORM) -> None:
        """
        Add the samples from the device to the metric service.
        """
