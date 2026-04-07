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


def test_snippets_help(runner):
    result = runner.invoke(cli, ["snippets", "--help"])
    assert result.exit_code == 0
    assert "list" in result.output
    assert "create" in result.output
    assert "delete" in result.output


@respx.mock
def test_snippets_list(runner):
    data = {
        "meta": {"total_count": 2},
        "items": [
            {"id": 1, "name": "Tech", "slug": "tech", "meta": {"type": "testapp.Category"}},
            {"id": 2, "name": "Science", "slug": "science", "meta": {"type": "testapp.Category"}},
        ],
    }
    respx.get(f"{BASE_URL}/snippets/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["snippets", "list", "testapp.Category"])
    assert result.exit_code == 0
    assert "Tech" in result.output


@respx.mock
def test_snippets_list_with_search(runner):
    data = {
        "meta": {"total_count": 1},
        "items": [
            {"id": 1, "name": "Tech", "slug": "tech", "meta": {"type": "testapp.Category"}},
        ],
    }
    route = respx.get(f"{BASE_URL}/snippets/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["snippets", "list", "testapp.Category", "--search", "tech"])
    assert result.exit_code == 0
    assert "search=tech" in str(route.calls[0].request.url)


@respx.mock
def test_snippets_get(runner):
    data = {"id": 1, "name": "Tech", "slug": "tech", "meta": {"type": "testapp.Category"}}
    respx.get(f"{BASE_URL}/snippets/1/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["snippets", "get", "testapp.Category", "1"])
    assert result.exit_code == 0
    assert "Tech" in result.output


@respx.mock
def test_snippets_create(runner):
    data = {"id": 3, "name": "Arts", "slug": "arts", "meta": {"type": "testapp.Category"}}
    route = respx.post(f"{BASE_URL}/snippets/").mock(return_value=Response(201, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["snippets", "create", "testapp.Category", "--field", "name:Arts", "--field", "slug:arts"],
        )
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["type"] == "testapp.Category"
    assert body["name"] == "Arts"
    assert body["slug"] == "arts"


@respx.mock
def test_snippets_update(runner):
    data = {"id": 1, "name": "Technology", "slug": "tech", "meta": {"type": "testapp.Category"}}
    route = respx.patch(f"{BASE_URL}/snippets/1/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["snippets", "update", "testapp.Category", "1", "--field", "name:Technology"],
        )
    assert result.exit_code == 0
    body = json.loads(route.calls[0].request.content)
    assert body["name"] == "Technology"
    assert "type=testapp.Category" in str(route.calls[0].request.url)


@respx.mock
def test_snippets_delete(runner):
    respx.delete(f"{BASE_URL}/snippets/1/").mock(return_value=Response(204))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "snippets", "delete", "testapp.Category", "1", "--yes"])
    assert result.exit_code == 0
    assert "Deleted" in result.output


@respx.mock
def test_snippets_delete_without_yes_noninteractive(runner):
    """Non-TTY environment should skip confirmation."""
    respx.delete(f"{BASE_URL}/snippets/1/").mock(return_value=Response(204))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["snippets", "delete", "testapp.Category", "1"])
    assert result.exit_code == 0


@respx.mock
def test_schema_snippets_flag(runner):
    data = [
        {"type": "testapp.Category", "verbose_name": "category", "fields_summary": ["id", "name", "slug"]},
    ]
    respx.get(f"{BASE_URL}/schema/snippets/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["schema", "--snippets"])
    assert result.exit_code == 0
    assert "testapp.Category" in result.output


@respx.mock
def test_schema_all_flag(runner):
    page_data = {"page_types": [{"type": "testapp.SimplePage", "verbose_name": "simple page", "fields_summary": ["id", "body"]}]}
    snippet_data = {"snippet_types": [{"type": "testapp.Category", "verbose_name": "category", "fields_summary": ["id", "name"]}]}
    respx.get(f"{BASE_URL}/schema/").mock(return_value=Response(200, json=page_data))
    respx.get(f"{BASE_URL}/schema/snippets/").mock(return_value=Response(200, json=snippet_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["schema", "--all"])
    assert result.exit_code == 0
    assert "testapp.SimplePage" in result.output
    assert "testapp.Category" in result.output
