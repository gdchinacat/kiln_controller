import httpx2
import pytest

from .conftest import TestClient, Root


def test_root_resource_lifecycle(client: TestClient) -> None:
    root = Root(a=1)

    #  create the root object and get a shadow for it
    root.post(client)
    _root = Root.model_validate(client.get(root._url).json())
    assert _root.id == root.id
    assert _root.a == root.a

    # update a value on the shadow
    _root.a = 2
    _root.put(client)

    # verify the original does not see the value until it is refreshed/get
    assert root.a == 1, "root should not be changed until refreshed"
    root.get()
    assert root.a == 2, "put and get did not update value"

    # delete the object
    root.delete()

    # verify it no longer exists
    with pytest.raises(httpx2.HTTPStatusError) as hse:
        _root.get()
    assert hse.value.response.status_code == httpx2.codes.NOT_FOUND
