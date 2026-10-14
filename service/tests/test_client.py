"""
Test the kiln_controller python client library.
"""

from collections.abc import Callable
from contextlib import contextmanager
import datetime
import os
import random
from typing import Any
import unittest

import httpx2
import pytest

from fixtures import kwargs
from kiln_controller.client import (
    Resource,
    Client,
    User,
    Device,
    Schedule,
    Phase,
    PhaseType,
)
from rest_client import ResourceList

from ._fixtures import (
    user_fixture,
    user_client,
    device_fixture,
    schedule_fixture,
    phase_fixture,
    assert_http_status_error,
)

type KilnControllerResource = User | Device | Schedule | Phase


def _test_list_add[T: KilnControllerResource](
    resource: T,
    resource_list: ResourceList[T, Any],
    iadd: bool = False,
) -> None:
    """
    helper to add an object to a resource list.
    iadd: bool: use += rather than .append()
    """
    # add it to the list
    if iadd:
        resource_list += (resource,)
    else:
        resource_list.append(resource)

    # Make sure the obj exists in the resource list when refreshed.
    resource_list.expire()

    # Resource may have write only fields (User.password, Device.auth_token)
    # that mismatch between resource and what the server has, look by id.
    assert next(r for r in resource_list if r.id == resource.id)


# todo - add test_---_user_to_list methods


@pytest.mark.parametrize("iadd", (True, False))
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture(skip_create=True)
def test_add_device_to_list(
    iadd: bool, device: Device, client: Client, **_: object
) -> None:
    _test_list_add(device, client.devices, iadd=True)


@pytest.mark.parametrize("iadd", (True, False))
@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture(skip_create=True)
def test_add_schedule_to_list(
    iadd: bool, schedule: Schedule, client: Client, **_: Any
) -> None:
    _test_list_add(schedule, client.schedules, iadd=True)


def _test_post(client: Client, resource: KilnControllerResource) -> None:
    """
    test that resources of type _type can be created using
    Resource.post(client)
    """
    assert (
        resource.id is None
    ), f"{resource} appears to have already been created"  # precondition check

    # test post success
    resource.post(client)

    assert resource.id is not None, "post failed to assign id to resource"

    # test post with resource.id fails
    with pytest.raises(AttributeError):
        resource.post()

    resource.refresh()


@ kwargs["user"] << user_fixture(skip_create=True)
def test_post_user(admin_client, user: User, **_):
    return _test_post(admin_client, user)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture(skip_create=True)
def test_post_device(client: Client, device: Device, **_: Any) -> None:
    return _test_post(client, device)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture(skip_create=True)
def test_post_schedule(client: Client, schedule: Schedule, **_: Any) -> None:
    return _test_post(client, schedule)


def _test_put(
    resource: KilnControllerResource, client: Client, skip_put_create: bool = False
) -> None:
    """
    test that resources of type _type can be created and updated using
    Resource.put(client)
    """
    if not skip_put_create:
        # test put create success
        # good chance this won't collide...right?
        resource.id = int(random.random() * 1000000)
        resource.put(client)
        assert resource.id is not None, "put failed to assign id to resource"

    # Test put without resource.id succeeds and doesn't create a new
    # resource.
    resource_dict = resource.model_dump(mode="json")
    url = resource._url
    del resource_dict["id"]
    resp = client._http_client.put(url, json=resource_dict).raise_for_status()
    assert resp.json()["id"] == resource.id

    # test put with resource.id succeeds, attribute changes
    name = resource.name * 2
    resource.name = name
    resource.put(client)

    # Verify name is updated by creating a new bare Resource with only
    # id and getting it with the client.
    resource2 = resource._testing_shadow()
    resource2.name = ""
    resource2.get(client)

    assert name == resource2.name, "name not updated in put"


@ kwargs["user"] << user_fixture(skip_create=True)
def test_put_user(user: User, admin_client: Client, **_):
    return _test_put(user, admin_client)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
def test_put_device(device: Device, client: Client, **_):
    return _test_put(device, client, skip_put_create=True)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture(skip_create=True)
def test_put_schedule(schedule: Schedule, client: Client, **_):
    return _test_put(schedule, client)


@contextmanager
def _mock_client_requests():
    """context manager that replaces client.requests with a mock"""
    mock = None
    try:
        yield mock
    finally:
        pass


def _test_delete_resource(resource: KilnControllerResource) -> None:
    """test that Resource.delete() functions"""
    assert resource.id is not None
    resource_id = resource.id

    resource.delete()

    assert resource.id is None
    resource.id = resource_id
    with assert_http_status_error(httpx2.codes.NOT_FOUND):
        resource.get()


@ kwargs["user"] << user_fixture(skip_delete=True)
def test_delete_user_resource(user: User, **_: Any):
    return _test_delete_resource(resource=user)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture(skip_delete=True)
def test_delete_device_resource(client, device, **kwargs):
    return _test_delete_resource(
        resource=device,
    )


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture(skip_delete=True)
def test_delete_schedule_resource(client, schedule, **kwargs):
    return _test_delete_resource(
        resource=schedule,
    )


def _test_delete_resource_by_list[T: KilnControllerResource](
    resource_list: ResourceList[T, Any], resource: T
) -> None:
    """test that Resource.delete() functions"""
    resource_id = resource.id
    _resource = resource._testing_shadow()

    # resource_list.expire()  # ensure the view is in sync with resource

    # Find the index of the resource by id because the resources may have write
    # only fields (user.password) that are on the fixture that created the
    # resource but not on the instances in the resource list.
    idx = next(i for (i, r) in enumerate(resource_list) if r.id == resource.id)

    del resource_list[idx]

    with assert_http_status_error(httpx2.codes.NOT_FOUND):
        _resource.get()  # getting the shadow fails because it's been deleted


@ kwargs["user"] << user_fixture(skip_delete=True)
@ kwargs["client"] << user_client()
def test_delete_user_resource_by_list(user: User, client: Client, **_: Any) -> None:
    return _test_delete_resource_by_list(client.users, user)


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["device"] << device_fixture()
def test_delete_device_resource_by_list(
    client: Client, device: Device, **kwargs
) -> None:
    return _test_delete_resource_by_list(
        client.devices,
        device,
    )


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture()
def test_delete_schedule_resource_by_list(
    client: Client, schedule: Schedule, **_: Any
) -> None:
    return _test_delete_resource_by_list(
        client.schedules,
        schedule,
    )


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture()
@ kwargs["phase"] << phase_fixture(skip_create=True, skip_delete=True)
def test_basic_schedule_phases_resource_list(
    phase: Phase, schedule: Schedule, **_: Any
) -> None:
    """basic test that schedule.phases ResourceList works"""
    assert [] == schedule.phases

    """
    phase = Phase(
        name="name",
        ordinal=1,
        phase_type=PhaseType.RAMP,
        temperature=None,
        duration=datetime.time(minute=5),
        parent=schedule,
    )
"""
    schedule.phases += (phase,)
    assert [phase] == schedule.phases

    del schedule.phases[0]
    assert [] == schedule.phases


@ kwargs["user"] << user_fixture()
@ kwargs["client"] << user_client()
@ kwargs["schedule"] << schedule_fixture(skip_delete=True)
@ kwargs["phase"] << phase_fixture(skip_delete=True)
def test_schedule_delete_deletes_phases(client, schedule, phase, **kwargs):
    """basic test that deleting a schedule deletes its phases"""
    _phase = phase._testing_shadow()
    schedule.delete()

    # phase get can't be made because its parent has been deleted
    with pytest.raises(AssertionError) as ae:
        phase.get()
    assert Resource.IDReason.HAS_BEEN_DELETED.value in ae.value.args[0]

    # shaddow request is made but phase has been deleted
    with assert_http_status_error(httpx2.codes.NOT_FOUND):
        _phase.get()
