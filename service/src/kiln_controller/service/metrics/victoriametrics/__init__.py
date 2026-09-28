"""
Victoria Metrics backed metric server..

Job: Kiln
Instance: Firing
"""

from fastapi import status
from collections.abc import Iterable
from dataclasses import dataclass
import httpx
import logging
import time
from typing import override, Any

from .. import MetricsServer
from ....device.protocol import Telemetry, Sample, Metrics
from ...models import DeviceORM

logger = logging.getLogger("kiln_controller.victoriametrics")


def metrics_for_sample(
    tags: dict[str, Any],
    timestamp: int,
    metrics: Metrics,
    name: str = "",
) -> Iterable[dict[str, Any]]:
    """
    Generate metrics like for the sample. Nested metrics will use dotted metric
    names.
    """
    # todo? - json is really heavyweight, consider using a more efficient
    #         way to inject the metrics. (this works for now though)
    for k, v in metrics.items():
        if isinstance(v, Metrics):
            yield from metrics_for_sample(tags, timestamp, v, f"{name}{k}.")
        else:
            metric = {
                "metric": f"{name}{k}",
                "timestamp": timestamp,
                "value": v,
                "tags": tags,
            }
            yield metric


@dataclass
class VictoriaMetricsServer(MetricsServer):
    url: str

    @override
    async def add_samples(self, device: DeviceORM, telemetry: Telemetry) -> None:
        logger.debug("add_samples {device} {samples}")

        delta = telemetry.timestamp_ms - int(time.time() * 1000)

        tags = {
            "job": str(device.id),
            # LH I don't think it is "correct" to add these ephemeral values as
            #    tags because (for example) changing the user seems to create a
            #    new series. While having them could be useful for querying
            #    them in metricsql, I think a single set of metrics by device
            #    is preferable to having them change when the user modifies
            #    things like names, operators, etc.
            # "device_name": device.name,
            # "user_id": str(device.user.id),
            # "user_name": device.user.name,
            #'instance': device.firing.id,  # todo - samples should probably have the firing id rather than patching it up here
            # todo? what else do metrics need to be looked up by
        }

        # todo telemetry metrics to track device status, reporting, time delta, etc
        json = list(
            metric
            for sample in telemetry.samples
            for metric in metrics_for_sample(tags, sample.timestamp, sample, "kiln.")
        )

        async with httpx.AsyncClient() as client:  # todo - reuse the same httpx client
            response = await client.put(self.url, json=json)
            if response.status_code == status.HTTP_204_NO_CONTENT:
                # todo send device the command to discard successful samples
                logger.error(
                    f"{len(json)} metrics sent successfully "
                    f"for {len(telemetry.samples)} samples "
                    f"for {', '.join(str(sample.timestamp) for sample in telemetry.samples)}."
                )
            else:
                logger.error(f"{response.status_code} {response.text=}")
