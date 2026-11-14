import pydantic

from ..metrics import MetricName

__all__ = ("MetricsRequest", "MetricsResponse", "MetricsSummary")


class MetricsRequest(pydantic.BaseModel):
    start: int | str | None = None
    end: int | str | None = None
    step: int | str | None = None


class MetricsSummary(pydantic.BaseModel):
    metrics: tuple[MetricName, ...]


class MetricsResponse(pydantic.BaseModel):
    times: list[int]
    values: list[int | float | None]
