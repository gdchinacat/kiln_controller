from collections.abc import Callable
from typing import Any, Literal, get_args

import httpx2
import pytest
from fixtures import kwargs

from kiln_controller.client import Device
from kiln_controller.service.metrics import MetricsServer
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

# todo - use mock victoria metrics service


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


@pytest.mark.parametrize("metric", supported_metrics())
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
def test_valid_metric_cursory(
    metric: Literal["uptime", "temperature"], device: Device, **_: Any
) -> None:
    metrics = device.metrics([metric])
    assert metrics.times
    assert len(metrics.series) == 1
    assert metrics.series[0].metric == metric
