import httpx2
import pytest

from .conftest import TestClient, Parent


def test_resource_lifecycle(client: TestClient) -> None:
    parent = Parent(a=1)

    #  create the parent object and get a shadow for it
    parent.post(client)
    _parent = Parent.model_validate(client._client.get(parent._url).json())
    assert _parent.id == parent.id
    assert _parent.a == parent.a

    # update a value on the shadow
    _parent.a = 2
    _parent.put(client)

    # verify the original does not see the value until it is refreshed/get
    assert parent.a == 1, "parent should not be changed until refreshed"
    parent.get()
    assert parent.a == 2, "put and get did not update value"

    # delete the object
    parent.delete()

    # verify it no longer exists
    with pytest.raises(httpx2.HTTPStatusError) as hse:
        _parent.get()
    assert hse.value.response.status_code == httpx2.codes.NOT_FOUND


def test_resource_list(client: TestClient) -> None:
    # no parents to start with
    assert client.parents == []

    # create a parent through the client
    parent = Parent(a=1)
    parent.post(client)

    # client resource list is stale, still has no parents
    assert len(client.parents) == 0

    # expiring the client causes it to reload
    client.expire()
    assert len(client.parents) == 1

    # delete the parent, but keep a (stale) reference to it
    _parent = Parent.model_validate(client._client.get(parent._url).json())
    del client.parents[0]

    # Verify the parent was actually deleted on the server by getting the stale
    # parent.
    with pytest.raises(httpx2.HTTPStatusError) as hse:
        _parent.get(client)
    assert hse.value.response.status_code == httpx2.codes.NOT_FOUND
