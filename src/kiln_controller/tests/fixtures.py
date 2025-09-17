"""
Common fixtures for tests.
"""
# pylint: disable=unused-argument


from skytap.fixtures.fixtures import default_fixture_name, pass_self
from kiln_controller.client.mock_service import MockService


@default_fixture_name('mock_service')
@pass_self
def mock_service(self, **_):
    return MockService()
