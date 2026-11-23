from typing import Literal

import pydantic

__all__ = (
    "METRICS_INFO",
    "MetricsRequest",
    "MetricsResponse",
    "MetricsSummary",
)


class MetricsRequest(pydantic.BaseModel):
    start: int | str | None = None
    end: int | str | None = None
    step: int | str | None = None


type Units = Literal[  # todo? naming
    "count",
    "temperature",
    "percent",
    "bytes",
    "seconds",
    "milliseconds",
]


class MetricInfo(pydantic.BaseModel):
    units: Units | None = (
        None  # todo? "units: None" should mean it is unitless, not that it shouldn't be displayed
    )
    name: str | None = None


type MetricsInfo = dict[str, MetricInfo]

METRICS_INFO: MetricsInfo = {
    "telemetry": MetricInfo(),
    "telemetry_state": MetricInfo(),
    "sample_count": MetricInfo(units="count", name="sample buffer ratio"),
    "time_delta": MetricInfo(units="milliseconds", name="time delta"),
    "uptime": MetricInfo(units="seconds"),
    "state": MetricInfo(),
    "temperature": MetricInfo(units="temperature"),
    "temperature.core": MetricInfo(
        units="temperature", name="core temperature"
    ),
    "temperature.target": MetricInfo(
        units="temperature", name="target temperature"
    ),
    "temperature.cold_junction": MetricInfo(
        units="temperature", name="cold junction temperature"
    ),
    "memory.size": MetricInfo(units="bytes", name="memory size"),
    "memory.heap_free": MetricInfo(units="bytes", name="heap free"),
    "memory.min_heap_free": MetricInfo(units="bytes", name="heap free (min)"),
    "memory.largest_allocatable": MetricInfo(
        units="bytes",
        name="largest allocatable",
    ),
    "memory.sample_buffer_size": MetricInfo(units="bytes", name="buffer size"),
    "duty_cycle": MetricInfo(units="percent", name="duty cycle"),
    "sub_sample_count": MetricInfo(
        units="count",
        name="oversampling ratio",
    ),
}


class MetricsSummary(pydantic.BaseModel):
    metrics: MetricsInfo


type MetricTime = int
type MetricValue = int | float | None
type MetricPoint = tuple[MetricTime, MetricValue]


class MetricsResponse(pydantic.BaseModel):
    values: list[MetricPoint]
