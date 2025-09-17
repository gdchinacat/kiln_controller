"""
Common fixtures for tests.
"""
# pylint: disable=unused-argument
# pylint: disable=redefined-outer-name


from skytap.fixtures.fixtures import default_fixture_name, pass_self
from kiln_controller.client.mock_service import MockService
from kiln_controller.client import Client

__all__ = ['mock_service_fixture', 'client_fixture']


@default_fixture_name('mock_service')
@pass_self
def mock_service_fixture(self, **_):
    '''fixture that provices a MockService'''
    return MockService()


@default_fixture_name('client')
@pass_self
def client_fixture(self, mock_service, **_):
    '''fixture that provides a Client'''
    with mock_service.patch():
        return Client()
