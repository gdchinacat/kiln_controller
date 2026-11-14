from typing import Literal

import pydantic

from rest_client import Resource, RestClient


class MetricsResponse(pydantic.BaseModel):
    values: list[tuple[int, int | float | None]]


class Device(Resource[RestClient]):
    _URL = "/device"

    version: int | None = None
    name: str
    user_id: int
    description: str | None = None
    auth_token: str | None = None  # only exists on responses to POST

    def metric(
        self, metric: Literal["uptime", "temperature"]
    ) -> MetricsResponse:
        response = self._client._http_client.get(
            f"{self._url}/metrics/{metric}"
        ).raise_for_status()
        return MetricsResponse.model_validate(response.json())
