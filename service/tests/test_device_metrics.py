"""
Test client.Device.metric and /devices/{device_id}/metrics/{metric}.

These tests stub out VictoriaMetricsServer. As such, they only test the client
and route pass-throughs, not the interaction between the service and
VictoriaMetrics.

todo - add tests that VictoriaMetricsService makes correct queries to
VictoriaMetrics query endpoint and packages results properly.
"""

from datetime import datetime
from typing import Any, TypeAliasType, get_args

import httpx2
import pytest
from fixtures import kwargs

from kiln_controller import client
from kiln_controller.client import Device
from kiln_controller.service.metrics import (
    DeviceP,
    MetricName,
    MetricsServer,
    QueryResult,
    Telemetry,
)
from kiln_controller.service.metrics.victoriametrics import (
    METRIC_NAME_MAP,
)

from ._fixtures import (
    assert_http_status_error,
    device_fixture,
    user_client,
    user_fixture,
)
from .conftest import StubMetricsServer


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
def test_invalid_metric_name(device: Device, **_: Any) -> None:
    with assert_http_status_error(httpx2.codes.UNPROCESSABLE_CONTENT):
        device.metric("invalid")  # type: ignore # intentional type error


def supported_metrics(
    metric_name_type: TypeAliasType = MetricName,
) -> tuple[str]:
    return get_args(metric_name_type.__value__)


def test_metrics_supported_consistently() -> None:
    assert set(METRIC_NAME_MAP.keys()) == set(supported_metrics(MetricName))
    assert set(supported_metrics(MetricName)) == set(
        supported_metrics(client.MetricName)
    )


def test_metrics_server_supported_metrics() -> None:
    class _MetricsServer(MetricsServer):
        async def close(self) -> None: ...
        async def telemetry(
            self, telemetry: Telemetry, device: DeviceP
        ) -> int: ...
        async def query(
            self,
            instance: int,
            metric: MetricName,
            start: int | None = None,
            end: int | None = None,
            step: int | None = None,
        ) -> QueryResult: ...

    assert _MetricsServer().supported_metrics == supported_metrics()


@kwargs.factory
def metric_server_query(
    metrics_server: StubMetricsServer,
    device: Device,
    metric: MetricName,
    start: datetime | None = None,
    end: datetime | None = None,
    step: int | None = None,
    **_,
) -> None:
    """
    @ kwargs['_'] << metric_server_query(...,
                                         query_result=QueryResult(...),
                                         ...)
    `instance` is set to device.id
    """
    metrics_server.mock_query(
        device.id,
        metric=metric,
        start=start,
        end=end,
        step=step,
        query_result=QueryResult([(0, 1)]),
    )


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
def test_metrics_summary(device: Device, **_: Any) -> None:
    summary = device.metrics_summary()
    assert set(summary.metrics) == set(supported_metrics())


@pytest.mark.parametrize("metric", supported_metrics())
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
@ kwargs["_"] << metric_server_query()
def test_valid_metric_cursory(
    metric: MetricName,
    device: Device,
    **_: Any,
) -> None:
    device.metric(metric)
    # no assertions on what is returned since it is whatever the stubs return
    # and would serve no purpose other than asserting the test matches the test
