"""
Common fixtures for tests.

Fixture implementations are encouraged to use Resource.post(client) rather than
creating them through resource lists. This is to avoid unnecessary requests
to populate the list on access and refresh the list after adding resources to
them. This has the drawback of allowing the resource lists on the client and
resources becoming stale. ResourceList.expire() should be used to indicate the
resource lists should be refreshed on next access.
"""

# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name


from functools import wraps
from itertools import count
import os
from random import randint
from unittest import TestCase

import inspect
from typing import Callable


def default_fixture_name(name: str):
    """Decorator to set the default fixture name for a factory.

    The original tests rely on get_default_fixture_name(factory) to refer to
    the kwarg name the fixture should be injected under. We store the name
    on the factory object.
    """

    def _decorator(obj):
        setattr(obj, "_default_fixture_name", name)
        return obj

    return _decorator


def get_default_fixture_name(factory: Callable) -> str:
    """Return the default fixture name for a factory.

    Fall back to the factory __name__ if no explicit name was provided.
    """
    return getattr(factory, "_default_fixture_name", factory.__name__)


def fixture(factory, **factory_kwargs):
    """Decorator to apply a factory as a fixture to a unittest TestCase

    Usage in tests is like:

        @fixture(user_fixture)
        def test_something(self, user):
            ...

    This decorator wraps the test method so that when it's invoked by
    unittest it will call the provided factory (trying to pass the TestCase
    instance if the factory accepts it) and inject the result into the
    test's kwargs using the factory's default name.
    """

    def decorator(test_func):
        def wrapper(self, *args, **kwargs):
            # Build keyword args to pass to the factory. Start with any
            # explicit factory kwargs from the decorator, then include any
            # fixtures already injected by outer wrappers (in `kwargs`).
            call_kwargs = dict(factory_kwargs)
            call_kwargs.update(kwargs)

            # Try calling factory without `self` first (this covers plain
            # functions and dataclass factories that accept named fixtures).
            try:
                resource = factory(**call_kwargs)
            except TypeError:
                # If that fails because the factory expects the TestCase
                # instance, try calling with `self` as the first argument.
                resource = factory(self, **call_kwargs)

            name = get_default_fixture_name(factory)
            # inject resource into kwargs under the fixture name
            kwargs[name] = resource
            return test_func(self, *args, **kwargs)

        # Preserve test function attributes
        wrapper.__name__ = test_func.__name__
        wrapper.__doc__ = test_func.__doc__
        return wrapper

    return decorator


import kiln_controller as kc
from .mock_service import MockService
from kiln_controller.common.enums import PhaseType

__all__ = [
    "CleanupTestCase",
    "mock_service_fixture",
    "client_fixture",
    "user_fixture",
    "schedule_fixture",
    "phase_fixture",
]


class CleanupTestCase(TestCase):
    """
    Mixin for adding cleanup functionality to tests.

    Primarily used by fixtures to remove resources created for tests, but test
    cases can also register resources for cleanup directly by calling:
    self.cleanup(mock_service, resource)

    SKIP_CLEANUP=true environment variable can be used to skip cleanup to allow
    inspection of the resources after the test completes.
    """

    def setUp(self):
        super().setUp()
        self._cleanup = []

    def tearDown(self):
        super().tearDown()
        for mock_service, resource in reversed(self._cleanup):
            with mock_service.patch():
                resource.delete()

    def cleanup(self, mock_service, resource):
        if os.getenv("SKIP_CLEANUP", "false").upper() != "TRUE":
            self._cleanup.append((mock_service, resource))


def cleanup(func):
    """
    Fixture to cleanup the return value of the decorated fixture function.

    Fixture functions decorated with this accept a skip_cleanup kwarg that is
    intercepted by this fixture. If skip_cleanup is true-ish no cleanup will
    be performed by the fixture for the resource. This is useful for tests that
    delete a resource provided by a fixture.
    """

    @wraps(func)
    def _cleanup(self, *, mock_service=None, skip_cleanup=None, **kwargs):
        """wrapper to call func and register its return for cleanup"""
        resource = func(self, mock_service=mock_service, **kwargs)
        if not skip_cleanup:
            self.cleanup(mock_service, resource)
        return resource

    return _cleanup


@default_fixture_name("mock_service")
def mock_service_fixture(self, **_):
    """fixture that provices a MockService"""
    return MockService()


@default_fixture_name("client")
def client_fixture(self, mock_service, **_):
    """fixture that provides a Client"""
    with mock_service.patch():
        return kc.Client()


@default_fixture_name("user")
@cleanup
def user_fixture(
    self,
    name="name",
    username=None,
    skip_create: bool = False,
    mock_service=None,
    client=None,
    _user_count=count(randint(0, 9999) * 1000),
    **kwargs,
):
    """
    Create a user.

    If username is not specified one is autogenerated to (hopefully) avoid
    conflict with existing user when running with LIVE_SERVICE=true. No attempt
    is made to actually ensure it doesn't conflict (it's random).

    skip_create causes the user to not be inserted (useful for when you need
    a user with a uniqueish username that hasn't been created on the server).
    """
    username = username or f"username{next(_user_count)}"
    user = kc.User(name, username)
    if not skip_create:
        with mock_service.patch():
            user.post(client)
    return user


@default_fixture_name("device")
@cleanup
def device_fixture(
    self,
    mock_service,
    client,
    name="name",
    host="host",
    port=5000,
    url="/",
    user_kwarg=get_default_fixture_name(user_fixture),
    **kwargs,
):
    user = kwargs[user_kwarg]
    device = kc.Device(name, user.id, host, port, url)
    with mock_service.patch():
        device.post(client)
    return device


@default_fixture_name("schedule")
@cleanup
def schedule_fixture(
    self,
    mock_service,
    client,
    user_kwarg=get_default_fixture_name(user_fixture),
    name="name",
    **kwargs,
):
    user = kwargs[user_kwarg]
    schedule = kc.Schedule(name=name, user_id=user.id)
    with mock_service.patch():
        schedule.post(client)
    return schedule


@default_fixture_name("phase")
def phase_fixture(
    self,
    mock_service,
    client,
    schedule_kwarg=get_default_fixture_name(schedule_fixture),
    name="name",
    ordinal=0,
    phase_type=PhaseType.RAMP,
    duration=None,
    temperature=1000,
    rate=100,
    **kwargs,
):
    """
    Fixture to create a phase.

    By default, the phase is a 1 hour long 1000C constant phase with ordinal 0.

    Cleanup is managed by the schedule, phases from this fixture are not
    scheduled for cleanup.
    """

    schedule = kwargs[schedule_kwarg]
    phase = kc.Phase(
        name=name,
        ordinal=ordinal,
        phase_type=phase_type,
        temperature=temperature,
        rate=rate,
        parent=schedule,
    )
    with mock_service.patch():
        phase.post(client)
    return phase
