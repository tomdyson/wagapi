from __future__ import annotations

import json
from unittest import mock

import pytest
import respx
from click.testing import CliRunner
from httpx import Response

from wagapi.cli import cli

BASE_URL = "https://cms.example.com/api/write/v1"
ENV = {"WAGAPI_URL": BASE_URL, "WAGAPI_TOKEN": "testtoken"}


@pytest.fixture
def runner():
    return CliRunner()


def test_help(runner):
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "wagapi" in result.output


def test_pages_help(runner):
    result = runner.invoke(cli, ["pages", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output


@respx.mock
def test_schema_list(runner):
    data = [{"name": "blog.BlogPage", "verbose_name": "blog page", "fields": ["title", "body"]}]
    respx.get(f"{BASE_URL}/schema/page-types/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["schema"])
    assert result.exit_code == 0
    assert "blog.BlogPage" in result.output


@respx.mock
def test_schema_detail(runner):
    data = {
        "name": "blog.BlogPage",
        "verbose_name": "blog page",
        "create_schema": {
            "required": ["title"],
            "properties": {"title": {"type": "string", "description": "Page title"}},
        },
        "allowed_parents": ["blog.BlogIndexPage"],
        "allowed_children": [],
    }
    respx.get(f"{BASE_URL}/schema/page-types/blog.BlogPage/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["schema", "blog.BlogPage"])
    assert result.exit_code == 0
    assert "blog.BlogPage" in result.output


@respx.mock
def test_schema_json_output(runner):
    data = [{"name": "blog.BlogPage", "verbose_name": "blog page"}]
    respx.get(f"{BASE_URL}/schema/page-types/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--json", "schema"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed[0]["name"] == "blog.BlogPage"


@respx.mock
def test_pages_list(runner):
    data = {
        "meta": {"total_count": 1},
        "items": [
            {
                "id": 42,
                "title": "Hello",
                "meta": {"type": "blog.BlogPage", "live": True},
            }
        ],
    }
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "list"])
    assert result.exit_code == 0
    assert "Hello" in result.output


@respx.mock
def test_pages_get(runner):
    data = {
        "id": 42,
        "title": "Hello",
        "slug": "hello",
        "meta": {"type": "blog.BlogPage", "live": False},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "get", "42"])
    assert result.exit_code == 0
    assert "Hello" in result.output


@respx.mock
def test_pages_create(runner):
    data = {
        "id": 42,
        "title": "Hello",
        "slug": "hello",
        "meta": {
            "type": "blog.BlogPage",
            "live": False,
            "has_unpublished_changes": True,
            "parent_id": 3,
        },
    }
    respx.post(f"{BASE_URL}/pages/").mock(return_value=Response(201, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["pages", "create", "blog.BlogPage", "--parent", "3", "--title", "Hello"],
        )
    assert result.exit_code == 0
    assert "42" in result.output


@respx.mock
def test_pages_create_with_body(runner):
    data = {
        "id": 43,
        "title": "Iris",
        "slug": "iris",
        "meta": {"type": "blog.BlogPage", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            [
                "pages", "create", "blog.BlogPage",
                "--parent", "3",
                "--title", "Iris",
                "--body", "## Early Life\n\nBorn in Dublin.",
            ],
        )
    assert result.exit_code == 0
    # Verify the request body contained streamfield blocks
    request_body = json.loads(route.calls[0].request.content)
    assert isinstance(request_body["body"], list)
    assert request_body["body"][0]["type"] == "heading"
    assert request_body["body"][1]["type"] == "paragraph"


@respx.mock
def test_pages_create_with_path_parent(runner):
    data = {
        "id": 44,
        "title": "Test",
        "slug": "test",
        "meta": {"type": "blog.BlogPage", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["pages", "create", "blog.BlogPage", "--parent", "/blog/", "--title", "Test"],
        )
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["parent"] == "/blog/"


@respx.mock
def test_pages_create_raw(runner):
    data = {
        "id": 45,
        "title": "Raw",
        "slug": "raw",
        "meta": {"type": "blog.BlogPage", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    body_json = '[{"type":"paragraph","value":"<p>Hello</p>","id":"abc123"}]'
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            [
                "pages", "create", "blog.BlogPage",
                "--parent", "3",
                "--title", "Raw",
                "--raw",
                "--body", body_json,
            ],
        )
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["body"][0]["type"] == "paragraph"


@respx.mock
def test_pages_update(runner):
    data = {"id": 42, "title": "Updated", "meta": {"type": "blog.BlogPage", "live": False}}
    respx.patch(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "update", "42", "--title", "Updated"])
    assert result.exit_code == 0
    assert "Updated" in result.output


@respx.mock
def test_pages_delete(runner):
    respx.delete(f"{BASE_URL}/pages/42/").mock(return_value=Response(204))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "pages", "delete", "42", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


@respx.mock
def test_pages_publish(runner):
    data = {"id": 42, "title": "Hello"}
    respx.post(f"{BASE_URL}/pages/42/publish/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "pages", "publish", "42"])
    assert result.exit_code == 0
    assert "Published" in result.output


@respx.mock
def test_pages_unpublish(runner):
    data = {"id": 42, "title": "Hello"}
    respx.post(f"{BASE_URL}/pages/42/unpublish/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "pages", "unpublish", "42"])
    assert result.exit_code == 0
    assert "Unpublished" in result.output


@respx.mock
def test_images_list(runner):
    data = {
        "meta": {"total_count": 1},
        "items": [{"id": 7, "title": "Hero"}],
    }
    respx.get(f"{BASE_URL}/images/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["images", "list"])
    assert result.exit_code == 0
    assert "Hero" in result.output


@respx.mock
def test_images_get(runner):
    data = {"id": 7, "title": "Hero", "width": 1200, "height": 800, "meta": {}}
    respx.get(f"{BASE_URL}/images/7/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["images", "get", "7"])
    assert result.exit_code == 0
    assert "Hero" in result.output


def test_no_config_error(runner):
    with mock.patch.dict("os.environ", {}, clear=True):
        with mock.patch("wagapi.config._read_toml", return_value={}):
            result = runner.invoke(cli, ["schema"])
    assert result.exit_code != 0
    assert "Not configured" in result.output


@respx.mock
def test_json_output_flag(runner):
    data = {
        "id": 42,
        "title": "Hello",
        "slug": "hello",
        "meta": {"type": "blog.BlogPage", "live": False},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--json", "pages", "get", "42"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["id"] == 42


@respx.mock
def test_create_with_field_option(runner):
    data = {
        "id": 46,
        "title": "Test",
        "slug": "test",
        "meta": {"type": "blog.BlogPage", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            [
                "pages", "create", "blog.BlogPage",
                "--parent", "3",
                "--title", "Test",
                "--field", "published_date:2026-04-06",
            ],
        )
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["published_date"] == "2026-04-06"
