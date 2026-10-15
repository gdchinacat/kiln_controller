from collections.abc import Generator, Callable, Iterator
from contextlib import contextmanager, AbstractContextManager
from dataclasses import dataclass
import os
import shutil
import ssl
from threading import Thread
import time
from typing import Generator

import fastapi
import httpx2
import pytest
from sqlalchemy.ext.asyncio import AsyncEngine
import trustme
import uvicorn

from kiln_controller.service.main import app
from kiln_controller.service.models import get_engine, get_sessionmaker, SessionMaker
from kiln_controller.client import Client

"""
Pytest fixtures. These are mostly relatively static fixtures that are not
parameterized (in the 'has parameters' sense, not the pytest.parametrize
sense). Test specific/parameterized fixtures used with fixtures.kwargs are
located in _fixtures.
"""


@dataclass
class Service:
    url: str
    ca: trustme.CA

    @property
    def client_ssl_context(self) -> ssl.SSLContext:
        context = ssl.create_default_context()
        context.load_verify_locations(cadata=self.ca.cert_pem.bytes().decode())
        return context


type ServiceFactory = Callable[[fastapi.FastAPI], AbstractContextManager[Service]]


@pytest.fixture(scope="session")
def service_factory() -> ServiceFactory:
    @contextmanager
    def _factory(app: fastapi.FastAPI) -> Iterator[Service]:
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

        # TODO - this service uses the global app defined in main which will cause
        #        all sorts of problems with any tests that use global app state
        #        (such as app.state.metrics_server).
        # TODO - replace app state service references such as sessionmaker and
        #        metrics_server.
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
    service: Service, username="admin", password="admin"
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
