"""
Pytest fixtures. These are mostly relatively static fixtures that are not
parameterized (in the 'has parameters' sense, not the pytest.parametrize
sense). Test specific/parameterized fixtures used with fixtures.kwargs are
located in _fixtures.
"""

import ssl
import time
from collections import deque
from collections.abc import Callable, Generator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from threading import Thread
from typing import Any, Literal, override

import fastapi
import httpx2
import pytest
import trustme
import uvicorn
from sqlalchemy.ext.asyncio import AsyncEngine

from kiln_controller.client import Client
from kiln_controller.service.main import app
from kiln_controller.service.metrics import (
    DeviceP,
    MetricsServer,
    QueryResult,
    Telemetry,
)
from kiln_controller.service.models import (
    SessionMaker,
    get_engine,
    get_sessionmaker,
)


@dataclass
class Service:
    url: str
    ca: trustme.CA

    @property
    def client_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=self.ca.cert_pem.bytes().decode())
        return context


type ServiceFactory = Callable[
    [fastapi.FastAPI], AbstractContextManager[Service]
]


@dataclass
class _MetricServerQueryArgs:
    instance: int
    metric: Literal["uptime", "temperature"]
    start: int | None = None
    end: int | None = None
    step: int | None = None

    def validate(self, *args: Any, **kwargs: Any) -> None:
        assert _MetricServerQueryArgs(*args, **kwargs) == self


@dataclass
class StubMetricsServer(MetricsServer):
    query_results: deque[tuple[_MetricServerQueryArgs, QueryResult]] = field(
        default_factory=deque
    )

    def mock_query(
        self, *args: Any, query_result: QueryResult, **kwargs: Any
    ) -> None:
        self.query_results.append(
            (_MetricServerQueryArgs(*args, **kwargs), query_result)
        )

    @override
    async def close(self) -> None: ...

    @override
    async def telemetry(
        self, telemetry: Telemetry, device: DeviceP
    ) -> int: ...

    @override
    async def query(
        self,
        instance: int,
        metric: Literal["uptime", "temperature"],
        start: int | None = None,
        end: int | None = None,
        step: int | None = None,
    ) -> QueryResult:
        args, result = self.query_results.popleft()
        args.validate(instance, metric, start, end, step)
        return result


@pytest.fixture(scope="session")
def metrics_server() -> MetricsServer:
    return StubMetricsServer()


@pytest.fixture(scope="session")
def service_factory(metrics_server: StubMetricsServer) -> ServiceFactory:
    @contextmanager
    def _factory(app: fastapi.FastAPI) -> Generator[Service]:
        ca = trustme.CA()
        cert = ca.issue_cert("localhost", "127.0.0.1")

        def ssl_context_factory(
            _config: uvicorn.Config,
            _default_factory: Callable[[], ssl.SSLContext],
        ) -> ssl.SSLContext:
            context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            with (
                cert.private_key_pem.tempfile() as key_file,
                cert.cert_chain_pems[0].tempfile() as cert_file,
            ):
                context.load_cert_chain(cert_file, key_file)

            return context

        config = uvicorn.Config(
            app=app,
            host="127.0.0.1",
            port=0,
            log_level="error",
            ssl_context_factory=ssl_context_factory,
        )

        server = uvicorn.Server(config)
        server_thread = Thread(target=server.run, daemon=True)
        server_thread.start()

        while not server.started:
            time.sleep(0.05)

        assigned_port = server.servers[0].sockets[0].getsockname()[1]

        app.state.metrics_server = metrics_server
        try:
            yield Service(f"https://127.0.0.1:{assigned_port}", ca)
        finally:
            server.should_exit = True
            server_thread.join()  # if this hangs make sure clients are being closed

    return _factory


@pytest.fixture
def service(service_factory: ServiceFactory) -> Generator[Service]:
    with service_factory(app) as service:
        yield service


@pytest.fixture(scope="function")
def admin_client(
    service: Service, username: str = "admin", password: str = "admin"
) -> Generator[Client]:
    with httpx2.Client(
        base_url=service.url,
        verify=service.client_ssl_context,
    ) as http_client:
        client = Client(http_client)
        client.login(username, password)
        yield client
        http_client.close()


@pytest.fixture
async def _engine() -> AsyncEngine:
    return await get_engine("sqlite+aiosqlite:///:memory:")


@pytest.fixture
def sessionmaker(_engine: AsyncEngine) -> SessionMaker:
    return get_sessionmaker(_engine)
