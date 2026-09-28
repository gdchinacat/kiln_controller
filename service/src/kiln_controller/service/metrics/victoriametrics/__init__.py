"""
Victoria Metrics backed metric server..

Tags:
    device_id - the Device.id of the kiln

TODO
    - (bug) I changed the tag for the device from 'job' to 'device_id' and the
      series for the two overlapped...sum'ing the two with a label_replace
      doubled the time_delta. I'm not exactly sure why this occurred.
        - artifact of time sync since the schedule is aligned to millis()? Not
          likely since the device didn't restart.
        - did client double-send the sample because a disconnect happened after
          the metrics were sent that caused the websocket to error and the
          sample discard not happen (tiny race, but conceivable). If VM has
          duplicate sample rejection it wouldn't apply in this case because the
          tags were different.
        - the 5s resolution the device was using at the time was higher than
          what VM supports so two different samples went into the same VM
          bucket and there only appeared to be an overlap (mismatched source
          and TSDB resolutions).

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
    for k, v in metrics.field_values():
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

        # delta is significantly higher (~70ms) when calculated here relative
        # to when it was calculated in the websocket route. todo? The main us
        # will be to tell when a device has unreliable connectivity...and tens
        # of milliseconds here won't really matter for that use case. If the
        # delta is consistently high and stable enough the timestamps for its
        # samples could be adjusted to account for connection latency (ie a
        # slow proxy), but honestly...I don't think a few seconds off really
        # matters much.
        delta = telemetry.timestamp_ms - int(time.time() * 1000)

        tags = {
            "device_id": str(device.id),
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

        json = list(
            metric
            for sample in telemetry.samples
            for metric in metrics_for_sample(tags, sample.timestamp, sample, "kiln.")
        )
        json += [
            {
                "metric": f"kiln.telemetry.{k}",
                "timestamp": int(telemetry.timestamp_ms / 1000),
                "value": v,
                "tags": tags,
            }
            for (k, v) in (
                ("sample_count", telemetry.sample_count),
                ("time_delta", delta),
                (
                    "status",
                    telemetry.state.state.value,  # todo - yuck..get rid of double-state
                ),
            )
        ]

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
