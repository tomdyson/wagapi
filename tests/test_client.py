from __future__ import annotations

import pytest
import respx
from httpx import Response

from wagapi.client import WagtailClient
from wagapi.exceptions import (
    AuthError,
    NetworkError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)


BASE_URL = "https://cms.example.com/api/write/v1"


@pytest.fixture
def client():
    c = WagtailClient(BASE_URL, "testtoken")
    yield c
    c.close()


@respx.mock
def test_list_page_types(client):
    data = [{"name": "blog.BlogPage", "verbose_name": "blog page"}]
    respx.get(f"{BASE_URL}/schema/page-types/").mock(
        return_value=Response(200, json=data)
    )
    result = client.list_page_types()
    assert result == data


@respx.mock
def test_get_page_type_schema(client):
    data = {"name": "blog.BlogPage", "create_schema": {}}
    respx.get(f"{BASE_URL}/schema/page-types/blog.BlogPage/").mock(
        return_value=Response(200, json=data)
    )
    result = client.get_page_type_schema("blog.BlogPage")
    assert result["name"] == "blog.BlogPage"


@respx.mock
def test_list_pages(client):
    data = {"meta": {"total_count": 1}, "items": [{"id": 1, "title": "Test"}]}
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=data))
    result = client.list_pages(type="blog.BlogPage")
    assert result["items"][0]["id"] == 1


@respx.mock
def test_get_page(client):
    data = {"id": 42, "title": "Hello"}
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=data))
    result = client.get_page(42)
    assert result["title"] == "Hello"


@respx.mock
def test_create_page(client):
    data = {"id": 42, "title": "Hello", "meta": {"type": "blog.BlogPage"}}
    respx.post(f"{BASE_URL}/pages/").mock(return_value=Response(201, json=data))
    result = client.create_page({"type": "blog.BlogPage", "parent": 3, "title": "Hello"})
    assert result["id"] == 42


@respx.mock
def test_update_page(client):
    data = {"id": 42, "title": "Updated"}
    respx.patch(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=data))
    result = client.update_page(42, {"title": "Updated"})
    assert result["title"] == "Updated"


@respx.mock
def test_delete_page(client):
    respx.delete(f"{BASE_URL}/pages/42/").mock(return_value=Response(204))
    client.delete_page(42)  # should not raise


@respx.mock
def test_publish_page(client):
    data = {"id": 42, "title": "Hello"}
    respx.post(f"{BASE_URL}/pages/42/publish/").mock(
        return_value=Response(200, json=data)
    )
    result = client.publish_page(42)
    assert result["id"] == 42


@respx.mock
def test_unpublish_page(client):
    data = {"id": 42, "title": "Hello"}
    respx.post(f"{BASE_URL}/pages/42/unpublish/").mock(
        return_value=Response(200, json=data)
    )
    result = client.unpublish_page(42)
    assert result["id"] == 42


@respx.mock
def test_auth_error(client):
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(401, json={"detail": "Invalid token"}))
    with pytest.raises(AuthError):
        client.list_pages()


@respx.mock
def test_permission_denied(client):
    respx.get(f"{BASE_URL}/pages/").mock(
        return_value=Response(403, json={"detail": "Forbidden"})
    )
    with pytest.raises(PermissionDeniedError):
        client.list_pages()


@respx.mock
def test_not_found(client):
    respx.get(f"{BASE_URL}/pages/999/").mock(
        return_value=Response(404, json={"detail": "Not found"})
    )
    with pytest.raises(NotFoundError):
        client.get_page(999)


@respx.mock
def test_validation_error(client):
    respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(422, json={"detail": "BlogPage cannot be created under HomePage"})
    )
    with pytest.raises(ValidationError) as exc_info:
        client.create_page({"type": "blog.BlogPage", "parent": 2, "title": "Test"})
    assert "BlogPage cannot be created" in str(exc_info.value)


@respx.mock
def test_list_images(client):
    data = {"meta": {"total_count": 1}, "items": [{"id": 7, "title": "Hero"}]}
    respx.get(f"{BASE_URL}/images/").mock(return_value=Response(200, json=data))
    result = client.list_images(search="Hero")
    assert result["items"][0]["id"] == 7


@respx.mock
def test_get_image(client):
    data = {"id": 7, "title": "Hero"}
    respx.get(f"{BASE_URL}/images/7/").mock(return_value=Response(200, json=data))
    result = client.get_image(7)
    assert result["title"] == "Hero"
