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
    if False:
        return func

    def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
        metric = func(*args, **kwargs)
        logger.error(f"created metric {metric}")
        return metric

    return wrap


@log_metrics
def metric(
    name: str, timestamp: int, value: Any, tags: dict[str, str]
) -> dict[str, Any]:
    return {
        "metric": name,
        "timestamp": timestamp,
        "value": value,
        "tags": tags,
    }


def metrics_for_sample(
    tags: dict[str, Any],
    timestamp: int,
    metrics: Metrics,
    prefix: str = "",
) -> Iterable[dict[str, Any]]:
    """
    Generate metrics like for the sample. Nested metrics will use dotted metric
    names.
    """
    # todo? - json is really heavyweight, consider using a more efficient
    #         way to inject the metrics. (this works for now though)
    for name, value in metrics.field_values():
        if isinstance(value, Metrics):
            yield from metrics_for_sample(tags, timestamp, value, f"{prefix}{name}.")
        else:
            yield metric(f"{prefix}{name}", timestamp, value, tags)


@dataclass
class VictoriaMetricsServer(MetricsServer):
    url: str

    # TODO - Metrics that need to be stored. Most of these are "metric info"
    #        metrics with a value of 1 and tags for the instance and its
    #        associated id. PromQL supoorts joining on these and providing the
    #        join value over time or filtering by that value.
    #   info metrics
    #
    #     user_id : _user_id
    #     firing_id
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
        timestamp = int(telemetry.timestamp_ms / 1000)
        delta = telemetry.timestamp_ms - int(time.time() * 1000)

        tags = {
            "job": JOB_NAME,
            "instance": str(device.id),
        }

        json: list[dict[str, Any]] = []

        # todo lots of code duplication here...Telemetry is just another Metric
        # to dump. Refactor so that Telemetry isn't special cased so this can
        # be just one call to a 'metrics_for(telemetry)' that replaces the
        # sample specifc one that handles values that are list[Metric]
        # one issue is samples would appear as children of telemetry rather
        # than as siblings.
        json += [
            metric(
                f"kiln.telemetry.{name}",
                timestamp,
                value,
                tags,
            )
            for (name, value) in (
                ("sample_count", telemetry.sample_count),
                ("time_delta", delta),
                ("uptime", telemetry.uptime),
                ("status", telemetry.state.state.value),
            )
        ]
        json += (
            metric(
                "kiln.info",
                timestamp,
                1,
                tags
                | {"user_id": str(device.user.id), "firing_id": str(device.firing.id)},
            ),
        )

        json += list(
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
