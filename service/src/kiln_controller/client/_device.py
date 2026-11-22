from typing import Literal

import pydantic

from rest_client import Resource, RestClient


class MetricInfo(pydantic.BaseModel):
    units: str | None
    name: str | None


type MetricsInfo = dict[str, MetricInfo]


class MetricsSummary(pydantic.BaseModel):
    metrics: MetricsInfo


type MetricTime = int
type MetricValue = int | float | None
type MetricPoint = tuple[MetricTime, MetricValue]


class MetricsResponse(pydantic.BaseModel):
    values: list[MetricPoint]


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


class Device(Resource[RestClient]):
    _URL = "/device"

    version: int | None = None
    name: str
    user_id: int
    description: str | None = None
    auth_token: str | None = None  # only exists on responses to POST

    def metrics_summary(self) -> MetricsSummary:
        response = self._client._http_client.get(
            f"{self._url}/metrics"
        ).raise_for_status()
        return MetricsSummary.model_validate(response.json())

    def metric(self, metric: MetricName) -> MetricsResponse:
        response = self._client._http_client.get(
            f"{self._url}/metrics/{metric}"
        ).raise_for_status()
        return MetricsResponse.model_validate(response.json())
