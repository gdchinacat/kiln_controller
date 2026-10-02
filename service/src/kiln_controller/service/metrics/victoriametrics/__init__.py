"""
Victoria Metrics backed metric server..

Tags:
    device_id - the Device.id of the kiln

TODO
    - kiln.info relationships (user_id, firing_id, etc) are assigned when the
      metrics are processed. This means changes to them won't be reflected in
      the metrics until the samples are delivered, which could be quite a while.
      An alternative is to track the changes in the application and do the
      joins in post processing (yuck) or provide that data to this metrics
      adapter so it can create info records with the proper timestamps and
      ids (almost as yucky but not done at post-processing, so a bit better).
      Deferred until there's a compelling reason to do better than at sample
      delivery time. todo?

"""

from collections.abc import Iterable, Callable
from dataclasses import dataclass
import datetime
from enum import Enum
import functools
import logging
import time
from typing import override, Any

from fastapi import status
import httpx

from .. import MetricsServer
from ....device.protocol import Telemetry, Sample, Metrics
from ...models import DeviceORM, UserORM, FiringORM

logger = logging.getLogger("kiln_controller.victoriametrics")

JOB_NAME = "kiln_controller"


def log_metrics[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
        metric = func(*args, **kwargs)
        logger.debug(metric)
        return metric

    return wrap


# @log_metrics
def metric(
    name: str, value: Any, timestamp: int, tags: dict[str, str]
) -> dict[str, Any]:
    return {
        "metric": name,
        "timestamp": timestamp,
        "value": value,
        "tags": tags,
    }


def metrics_for_sample(
    prefix: str,
    metrics: Metrics,
    timestamp: int,
    tags: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    """
    Generate metrics like for the sample. Nested metrics will use dotted metric
    names.
    """
    # todo? - json is really heavyweight, consider using a more efficient
    #         way to inject the metrics. (this works for now though)
    for name, value in metrics.field_values():
        match value:
            case Metrics():
                yield from metrics_for_sample(
                    f"{prefix}{name}.", value, timestamp, tags
                )
            case Iterable():
                # prefix is hardcoded because that's where samples go, so make sure
                # this is only applied to Samples
                assert all(type(x) is Sample for x in value)
                yield from (
                    metric
                    for sample in value
                    for metric in metrics_for_sample(
                        "kiln.", sample, sample.timestamp, tags
                    )
                )
            case Enum():
                # name hack is to remove extra state in kiln.telemetry.state.state
                yield metric(f"{prefix}"[:-1], value.value, timestamp, tags)
            case _:
                yield metric(f"{prefix}{name}", value, timestamp, tags)


@dataclass
class VictoriaMetricsServer(MetricsServer):
    url: str

    @override
    async def telemetry(self, telemetry: Telemetry, device: DeviceORM) -> None:
        # delta is significantly higher (~70ms) when calculated here relative
        # to when it was calculated in the websocket route. todo? The main us
        # will be to tell when a device has unreliable connectivity...and tens
        # of milliseconds here won't really matter for that use case. If the
        # delta is consistently high and stable enough the timestamps for its
        # samples could be adjusted to account for connection latency (ie a
        # slow proxy), but honestly...I don't think a few seconds off really
        # matters much.
        timestamp = int(telemetry.timestamp_ms / 1000)
        delta = telemetry.timestamp_ms - int(time.time() * 1000)

        tags = {"job": JOB_NAME, "instance": str(device.id)}

        json: list[dict[str, Any]] = (
            [  # json (the core cpython library) does not support Iterable
                metric("kiln.telemetry.time_delta", delta, timestamp, tags),
                metric(
                    "kiln.info",
                    1,
                    timestamp,
                    tags
                    | {
                        "user_id": str(device.user.id),
                        "firing_id": str(device.firing.id),
                    },
                ),
                *metrics_for_sample(f"kiln.telemetry.", telemetry, timestamp, tags),
            ]
        )

        async with httpx.AsyncClient() as client:  # todo - reuse the same httpx client
            response = await client.put(self.url, json=json)
            if response.status_code == status.HTTP_204_NO_CONTENT:
                # todo send device the command to discard successful samples
                logger.debug(
                    f"{len(json)} metrics sent successfully "
                    f"for {len(telemetry.samples)} samples "
                    f"for {', '.join(str(sample.timestamp) for sample in telemetry.samples)}."
                )
            else:
                logger.error(f"{response.status_code} {response.text=}")
