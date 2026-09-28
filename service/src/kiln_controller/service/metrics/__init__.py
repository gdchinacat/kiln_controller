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
    async def add_samples(self, device: DeviceORM, telemetry: Telemetry) -> None:
        """
        Add the samples from the device to the metric service.
        """
