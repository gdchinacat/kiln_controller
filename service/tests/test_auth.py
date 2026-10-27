from typing import Any

import httpx2
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
    client.login(user.username, user.password)

    assert user.get()


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


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
def test_logout(client: Client, user: User, **_: Any) -> None:
    assert user.get()
    client.logout()

    with assert_http_status_error(httpx2.codes.UNAUTHORIZED):
        assert user.get()
