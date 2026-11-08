"""
Test the kiln_controller user resource behavior.
"""

from typing import Any

import httpx2
from fixtures import kwargs

from kiln_controller.client import Client, Device, User

from ._fixtures import (
    assert_http_status_error,
    device_fixture,
    schedule_fixture,
    user_client,
    user_fixture,
)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture()
def test_user_delete_fails_with_schedule(
    client: Client, user: User, **_: Any
) -> None:
    """
    Verify an error occurs if a user delete is attempted while the user has
    schedules.
    """
    with assert_http_status_error(httpx2.codes.UNPROCESSABLE_CONTENT) as hse:
        user.delete()
    assert (
        hse.value.response.json()["detail"][0]["type"] == "USER_HAS_SCHEDULES"
    )


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
def test_user_delete_fails_with_device(
    user: User, device: Device, **_: Any
) -> None:
    """
    Verify an error occurs if a user delete is attempted while the user has
    schedules.
    """
    assert device.user_id == user.id
    with assert_http_status_error(httpx2.codes.UNPROCESSABLE_CONTENT) as hse:
        user.delete()
    assert (
        hse.value.response.json()["detail"][0]["type"]
        == "USER_MANAGES_DEVICES"
    )


@ kwargs["user"] << user_fixture()
def test_user_get_has_no_password(user: User, **_: Any) -> None:
    user.password = None  # clear the password cached by fixtures
    user.get()
    assert not user.password


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
def test_user_list_has_no_password(client: Client, **_: Any) -> None:
    assert not any(user.password for user in client.expire().users)
    assert not any(user.password for user in client.users.refresh())


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
def test_auth_me_has_no_password(client: Client, **_: Any) -> None:
    assert not client.me.password


@ kwargs["user"] << user_fixture()
def test_user_not_found(user: User, **_: Any) -> None:
    user_id = user.id
    user.delete()
    user.id = user_id
    with assert_http_status_error(httpx2.codes.NOT_FOUND):
        user.get()
