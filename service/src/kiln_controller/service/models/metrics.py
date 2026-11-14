import pydantic

__all__ = ("MetricsRequest", "MetricsResponse", "MetricsSummary")


class MetricsRequest(pydantic.BaseModel):
    start: int | None = None
    end: int | None = None
    step: int | None = pydantic.Field(default=None, gt=0)


class MetricsSummary(pydantic.BaseModel):
    metrics: tuple[str, ...]
    # metrics: tuple[MetricName]


class MetricsResponse(pydantic.BaseModel):
    times: list[int]
    values: list[int | float | None]
