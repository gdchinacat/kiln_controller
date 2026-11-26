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
    "samples",
    "celcius",
    "percent",
    "bytes",
    "seconds",
    "milliseconds",
]


class MetricInfo(pydantic.BaseModel):
    units: Units | None = None


type MetricsInfo = dict[str, MetricInfo]

METRICS_INFO: MetricsInfo = {
    "telemetry": MetricInfo(),
    "telemetry_state": MetricInfo(),
    "sample_count": MetricInfo(units="samples"),
    "time_delta": MetricInfo(units="milliseconds"),
    "uptime": MetricInfo(units="seconds"),
    "state": MetricInfo(),
    "temperature": MetricInfo(units="celcius"),
    "temperature.core": MetricInfo(units="celcius"),
    "temperature.target": MetricInfo(units="celcius"),
    "temperature.cold_junction": MetricInfo(units="celcius"),
    "memory.size": MetricInfo(units="bytes"),
    "memory.heap_free": MetricInfo(units="bytes"),
    "memory.min_heap_free": MetricInfo(units="bytes"),
    "memory.largest_allocatable": MetricInfo(units="bytes"),
    "memory.sample_buffer_size": MetricInfo(units="bytes"),
    "duty_cycle": MetricInfo(units="percent"),
    "sub_sample_count": MetricInfo(units="samples"),
}


class MetricsSummary(pydantic.BaseModel):
    metrics: MetricsInfo


type MetricTime = int
type MetricValue = int | float | None
type MetricPoint = tuple[MetricTime, MetricValue]


class MetricsResponse(pydantic.BaseModel):
    values: list[MetricPoint]
