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

import logging
import os
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Literal, override

import httpx2
import pydantic
from fastapi import status

from ...device.protocol import Metrics, Sample, Telemetry
from ..models import DeviceORM
from . import MetricsServer, QueryResult, Series

logger = logging.getLogger("kiln_controller.victoriametrics")

JOB_NAME = "kiln_controller"

METRIC_NAME_MAP = {
    "uptime": "kiln.telemetry.uptime",
    "temperature": "kiln.temperature.current",
    # todo all the metrics!!!
}


def log_metrics[**P, R](func: Callable[P, R]) -> Callable[P, R]:
    if "KILN_CONTROLLER_LOG_METRICS" not in os.environ:
        return func

    def wrap(*args: P.args, **kwargs: P.kwargs) -> R:
        metric = func(*args, **kwargs)
        logger.error(metric)
        return metric

    return wrap


@log_metrics
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
    opentsdb_url: str

    client: httpx2.AsyncClient = field(
        default_factory=httpx2.AsyncClient, init=False
    )

    @override
    async def telemetry(self, telemetry: Telemetry, device: DeviceORM) -> int:
        # delta is significantly higher (~70ms) when calculated here relative
        # to when it was calculated in the websocket route. todo? The main use
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
                *metrics_for_sample(
                    "kiln.telemetry.", telemetry, timestamp, tags
                ),
            ]
        )

        response = await self.client.put(
            f"{self.opentsdb_url}/api/put", json=json
        )
        response.raise_for_status()
        if response.status_code == status.HTTP_204_NO_CONTENT:
            logger.debug(
                f"{len(json)} metrics sent successfully "
                f"for {len(telemetry.samples)} samples "
                f"for {', '.join(str(sample.timestamp) for sample in telemetry.samples)}."
            )
            return telemetry.samples[-1].timestamp if telemetry.samples else 0
        else:
            logger.error(f"{response.status_code} {response.text=}")
            return 0

    @override
    async def query(
        self,
        instance: int,
        metrics: list[Literal["uptime", "temperature"]],
        start: datetime | None = None,
        end: datetime | None = None,
        step: int | None = None,
    ) -> QueryResult:
        end = end or datetime.now()
        start = start or (
            end - timedelta(minutes=5)  # todo? policy for default window
        )
        step = step or 5

        # todo  support multiple metrics
        assert len(metrics) == 1
        metric = METRIC_NAME_MAP[metrics[0]]

        if metric == "uptime":
            metric = "telemetry.uptime"

        url = f'{self.url}/api/v1/query_range?query={metric}{{instance="{instance}",job="kiln_controller"}}&step={step}s'

        response = (await self.client.get(url)).raise_for_status().json()
        query_result = _QueryResult.model_validate(response)

        assert query_result.status == "success"  # todo proper error
        assert query_result.stats.seriesFetched == 1  # todo proper error
        assert query_result.data.resultType == "matrix"  # todo proper error
        assert len(query_result.data.result) == 1  # todo proper error

        result = query_result.data.result[0]
        assert result.metric.name == metric
        assert result.metric.instance == str(instance)
        assert result.metric.job == "kiln_controller"

        times, values = map(list, zip(*result.values))
        times = [datetime.fromtimestamp(t, tz=UTC) for t in times]
        return QueryResult(times=times, series=[Series(metrics[0], values)])


class _Metric(pydantic.BaseModel):
    name: str = pydantic.Field(alias="__name__")
    instance: str
    job: str


class _Result(pydantic.BaseModel):
    metric: _Metric
    values: list[tuple[int, int]]


class _Data(pydantic.BaseModel):
    result: list[_Result]
    resultType: str


class _Stats(pydantic.BaseModel):
    executionTimeMsec: int
    seriesFetched: int


class _QueryResult(pydantic.BaseModel):
    data: _Data
    stats: _Stats
    status: str
