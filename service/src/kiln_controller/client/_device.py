from datetime import datetime
from typing import Literal

import pydantic

from rest_client import Resource, RestClient


class Series(pydantic.BaseModel):
    metric: str
    values: list[int | float | None]


class MetricsResponse(pydantic.BaseModel):
    times: list[datetime]
    series: list[Series]


class Device(Resource[RestClient]):
    _URL = "/device"

    version: int | None = None
    name: str
    user_id: int
    description: str | None = None
    auth_token: str | None = None  # only exists on responses to POST

    def metrics(
        self, metrics: list[Literal["uptime", "temperature"]]
    ) -> MetricsResponse:
        response = self._client._http_client.post(
            f"{self._url}/metrics", json={"metrics": metrics}
        ).raise_for_status()
        return MetricsResponse.model_validate(response.json())
