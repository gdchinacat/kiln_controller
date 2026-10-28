from collections.abc import Callable
from typing import Any

import httpx2
import pytest
from fixtures import kwargs

from kiln_controller.client import Client

from ._fixtures import (
    User,
    assert_http_status_error,
    user_client,
    user_fixture,
)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client(skip_login=True)
def test_login(client: Client, user: User, **_: Any) -> None:
    assert user.password

    with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
        assert user.get()
    _user = client.login(user.username, user.password)

    assert user.get()

    user.password = None
    assert _user.model_dump() == user.model_dump()


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client(skip_login=True)
def test_login_fail(client: Client, user: User, **_: Any) -> None:
    assert user.password

    with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
        assert user.get()

    for username, password in ((user.username, ""), ("", user.password)):

        # login failure with badd username/password
        with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
            client.login(user.username, "")  # bad password

        # still not logged in
        with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
            assert user.get()


@pytest.mark.parametrize("method", (httpx2.Client.get, httpx2.Client.post))
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
def test_logout(
    method: Callable[..., httpx2.Response],
    client: Client,
    user: User,
    **_: Any,
) -> None:
    assert user.get()
    client.logout(method=method)

    with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
        assert user.get()


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client(skip_login=True)
def test_logout_no_session(client: Client, **_: Any) -> None:
    assert not client._http_client.cookies
    client.logout()


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
def test_logout_not_logged_in(client: Client, user: User, **_: Any) -> None:
    # ensure user is logged in to make sure client has a session
    assert user.get()

    client.logout()
    with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
        assert user.get()

    client.logout()


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
def test_me(client: Client, user: User, **_: Any) -> None:
    http_client = client._http_client
    user_json = user.model_dump(mode="json")
    user_json.pop("password")

    response = http_client.get("/auth/me").raise_for_status()
    assert response.json() == user_json
