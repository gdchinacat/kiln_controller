"""
Test client.Device.metrics and /devices/{device_id}/metrics.

These tests stub out VictoriaMetricsServer. As such, they only test the client
and route pass-throughs, not the interaction between the service and
VictoriaMetrics.

todo - add tests that VictoriaMetricsService makes correct queries to
VictoriaMetrics query endpoint and packages results properly.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal, get_args

import httpx2
import pytest
from fixtures import kwargs

from kiln_controller.client import Device
from kiln_controller.service.metrics import MetricsServer, QueryResult, Series
from kiln_controller.service.metrics.victoriametrics import (
    METRIC_NAME_MAP,
    VictoriaMetricsServer,
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
        device.metrics(["invalid"])  # type: ignore # intentional type error


def supported_metrics(
    func: Callable[..., Any] = MetricsServer.query,
) -> tuple[str, ...]:
    """Get the metrics supported by the MetricsServer.query method"""
    return get_args(get_args(func.__annotations__["metrics"])[0])


def test_metrics_server_metric_types_consistent_across_stack() -> None:
    """
    The set of metrics is duplicated several places (to avoid dependencies,
    internal mappings, etc. These need to stay in sync to ensure runtime
    exceptions don't occur or metrics are available when they should be. This
    test verifies this consistency. It also provides a list of all the places
    that need to be updated when adding/removing a metric.
    """
    metrics = supported_metrics()
    assert metrics == supported_metrics(MetricsServer.query)
    assert metrics == supported_metrics(Device.metrics)
    assert set(METRIC_NAME_MAP.keys()) == set(metrics)
    assert metrics == supported_metrics(VictoriaMetricsServer.query)


@kwargs.factory
def metric_server_query(
    metrics_server: StubMetricsServer,
    device: Device,
    metric: Literal["uptime", "temperature"],
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
        metrics=[metric],
        start=start,
        end=end,
        step=step,
        query_result=QueryResult(
            [datetime.fromtimestamp(0, tz=UTC)], [Series(metric, [1])]
        ),
    )


@pytest.mark.parametrize("metric", supported_metrics())
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
@ kwargs["_"] << metric_server_query()
def test_valid_metric_cursory(
    metric: Literal["uptime", "temperature"], device: Device, **_: Any
) -> None:
    device.metrics([metric])
    # no assertions on what is returned since it is whatever the stubs return
    # and would serve no purpose other than asserting the test matches the test
