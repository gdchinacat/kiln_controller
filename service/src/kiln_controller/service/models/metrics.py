from datetime import datetime
from typing import Literal

import pydantic

__all__ = ("MetricsRequest", "MetricsResponse", "Series")


class MetricsRequest(pydantic.BaseModel):
    # todo add the rest of the metrics
    metrics: list[Literal["uptime", "temperature"]] = pydantic.Field(
        min_length=1
    )
    start: datetime | None = None
    end: datetime | None = None
    step: int | None = pydantic.Field(default=None, gt=0)


class Series(pydantic.BaseModel):
    metric: str
    values: list[int | float | None]


class MetricsResponse(pydantic.BaseModel):
    times: list[datetime]
    series: list[Series]
