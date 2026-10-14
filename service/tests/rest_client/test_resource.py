import httpx2
import pytest

from .conftest import TestClient, Parent, Child
from rest_client import Resource


def test_resource_lifecycle(client: TestClient) -> None:
    parent = Parent(a=1)
    assert parent._id_reason == Resource.IDReason.NOT_YET_CREATED

    #  create the parent object and get a shadow for it
    parent.post(client)
    _parent = Parent.from_response(client._http_client.get(parent._url), client)
    assert _parent._id_reason == Resource.IDReason.DOES_HAVE_AN_ID
    assert _parent is not parent

    # Update a value.
    parent.a = 2
    parent.put(client)
    assert parent._id_reason == Resource.IDReason.DOES_HAVE_AN_ID

    # Verify the shadow does not see the value until it is refreshed/get().
    assert _parent.a == 1, "parent should not be changed until refreshed"
    _parent.get()
    assert _parent.a == 2, "put and get did not update value"

    # delete the object
    parent.delete()
    assert parent._id_reason == Resource.IDReason.HAS_BEEN_DELETED

    # Verify shadow sees it as not existing.
    with pytest.raises(httpx2.HTTPStatusError) as hse:
        _parent.get()
    assert hse.value.response.status_code == httpx2.codes.NOT_FOUND


def test_resource_list_refresh(client: TestClient) -> None:
    # no parents to start with
    assert client.parents == []

    # Create a parent through the resource.
    parent = Parent(a=1).post(client)

    # Client resource list is stale, still has no parents
    assert len(client.parents) == 0

    # expiring the client causes it to reload
    client.expire()
    assert len(client.parents) == 1

    # delete the parent, but keep a (stale) reference to it
    _parent = Parent.from_response(client._http_client.get(parent._url), client)
    del client.parents[0]

    # Verify the parent was actually deleted on the server by getting the stale
    # parent.
    with pytest.raises(httpx2.HTTPStatusError) as hse:
        _parent.get(client)
    assert hse.value.response.status_code == httpx2.codes.NOT_FOUND


@pytest.fixture
def parent(client: TestClient) -> Parent:
    parent = Parent(a=1)
    client.parents.append(parent)
    return parent


@pytest.mark.parametrize("iadd", (True, False))
def test_resource_list_lifecycle(
    client: TestClient,
    parent: Parent,
    iadd: bool,
) -> None:

    # no children
    assert parent.children == []

    # create a child and append it to parents children resource list
    child = Child(a=1)
    if iadd:
        parent.children += (child,)
    else:
        parent.children.append(child)
    assert isinstance(child._client, TestClient)

    # peek into the internals to make sure the resource list is expired
    assert parent.children._expired

    # Accessing the resource list refreshes it and includes the child.
    assert parent.children[0]._id_reason == child._id_reason
    assert parent.children == [child]

    # delete the child through the resource list
    del parent.children[0]

    # peek into the internals to make sure the resource list is expired
    assert parent.children._expired
    assert parent.children == []
