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
    respx.get(f"{BASE_URL}/schema/").mock(
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
    respx.get(f"{BASE_URL}/schema/blog.BlogPage/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["schema", "blog.BlogPage"])
    assert result.exit_code == 0
    assert "blog.BlogPage" in result.output


@respx.mock
def test_schema_json_output(runner):
    data = [{"name": "blog.BlogPage", "verbose_name": "blog page"}]
    respx.get(f"{BASE_URL}/schema/").mock(
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
def test_pages_list_with_parent(runner):
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
    route = respx.get(f"{BASE_URL}/pages/").mock(
        return_value=Response(200, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "list", "--parent", "5"])
    assert result.exit_code == 0
    assert route.called
    assert "parent" in str(route.calls[0].request.url)


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
def test_pages_create_with_body_streamfield(runner):
    """Body is converted to StreamField blocks when the field is a StreamField."""
    schema = {"streamfield_blocks": {"body": [{"type": "heading"}, {"type": "paragraph"}]}}
    respx.get(f"{BASE_URL}/schema/blog.BlogPage/").mock(
        return_value=Response(200, json=schema)
    )
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
    request_body = json.loads(route.calls[0].request.content)
    assert isinstance(request_body["body"], list)
    assert request_body["body"][0]["type"] == "heading"
    assert request_body["body"][1]["type"] == "paragraph"


@respx.mock
def test_pages_create_with_body_richtext(runner):
    """Body is sent as richtext format dict when the field is a RichTextField."""
    schema = {"streamfield_blocks": {}}
    respx.get(f"{BASE_URL}/schema/home.SimplePage/").mock(
        return_value=Response(200, json=schema)
    )
    data = {
        "id": 50,
        "title": "About",
        "slug": "about",
        "meta": {"type": "home.SimplePage", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            [
                "pages", "create", "home.SimplePage",
                "--parent", "3",
                "--title", "About",
                "--body", "Hello **world**",
            ],
        )
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert isinstance(request_body["body"], dict)
    assert request_body["body"]["format"] == "markdown"
    assert request_body["body"]["content"] == "Hello **world**"


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
def test_pages_update_with_body_richtext(runner):
    """Update fetches the page type and sends richtext for RichTextField."""
    # Mock GET to fetch the page (to learn its type)
    page_data = {
        "id": 42, "title": "Old", "body": "<p>old</p>",
        "meta": {"type": "home.SimplePage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    # Mock schema lookup
    schema = {"streamfield_blocks": {}}
    respx.get(f"{BASE_URL}/schema/home.SimplePage/").mock(
        return_value=Response(200, json=schema)
    )
    # Mock PATCH
    updated = {**page_data, "body": "<p>new</p>"}
    route = respx.patch(f"{BASE_URL}/pages/42/").mock(
        return_value=Response(200, json=updated)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "update", "42", "--body", "new content"])
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert isinstance(request_body["body"], dict)
    assert request_body["body"]["format"] == "markdown"


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


# -- Block type remapping tests ------------------------------------------------


@respx.mock
def test_pages_create_remap_paragraph_to_text(runner):
    """paragraph blocks are remapped to text when schema only allows text."""
    schema = {"streamfield_blocks": {"body": [{"type": "text"}, {"type": "map_embed"}]}}
    respx.get(f"{BASE_URL}/schema/events.EventPage/").mock(
        return_value=Response(200, json=schema)
    )
    data = {
        "id": 50, "title": "Ev", "slug": "ev",
        "meta": {"type": "events.EventPage", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["pages", "create", "events.EventPage",
             "--parent", "3", "--title", "Ev",
             "--body", "Hello world"],
        )
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["body"][0]["type"] == "text"


@respx.mock
def test_pages_create_block_warning_on_unknown(runner):
    """Warn on stderr when no remap exists for a generated block type."""
    schema = {"streamfield_blocks": {"body": [{"type": "map_embed"}]}}
    respx.get(f"{BASE_URL}/schema/events.EventPage/").mock(
        return_value=Response(200, json=schema)
    )
    data = {
        "id": 51, "title": "Ev", "slug": "ev",
        "meta": {"type": "events.EventPage", "live": False, "parent_id": 3},
    }
    respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["pages", "create", "events.EventPage",
             "--parent", "3", "--title", "Ev",
             "--body", "Hello"],
        )
    assert result.exit_code == 0
    assert "Warning" in result.output


@respx.mock
def test_pages_create_block_passthrough_no_schema(runner):
    """Blocks pass through unchanged when schema lookup fails."""
    respx.get(f"{BASE_URL}/schema/bad.Type/").mock(
        return_value=Response(404, json={"detail": "Not found"})
    )
    data = {
        "id": 52, "title": "X", "slug": "x",
        "meta": {"type": "bad.Type", "live": False, "parent_id": 3},
    }
    route = respx.post(f"{BASE_URL}/pages/").mock(
        return_value=Response(201, json=data)
    )
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(
            cli,
            ["pages", "create", "bad.Type",
             "--parent", "3", "--title", "X",
             "--body", "Hello"],
        )
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["body"][0]["type"] == "paragraph"


# -- pages get by path tests ---------------------------------------------------


@respx.mock
def test_pages_get_by_path(runner):
    """Get page by URL path resolves via list then fetches detail."""
    list_data = {
        "items": [{"id": 42, "title": "Hello", "meta": {"type": "blog.BlogPage", "live": True}}],
        "meta": {"total_count": 1},
    }
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=list_data))
    detail_data = {
        "id": 42, "title": "Hello", "slug": "hello",
        "meta": {"type": "blog.BlogPage", "live": True, "url_path": "/blog/hello/"},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=detail_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "get", "/blog/hello/"])
    assert result.exit_code == 0
    assert "Hello" in result.output


@respx.mock
def test_pages_get_by_path_not_found(runner):
    """Get page by nonexistent path returns not-found error."""
    list_data = {"items": [], "meta": {"total_count": 0}}
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=list_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["pages", "get", "/nonexistent/"])
    assert result.exit_code != 0
    assert "No page found" in result.output


# -- pages find tests ----------------------------------------------------------


@respx.mock
def test_pages_find(runner):
    """Find pages by search query."""
    data = {
        "meta": {"total_count": 1},
        "items": [
            {"id": 15, "title": "Iris Murdoch", "meta": {"type": "blog.BlogPage", "live": True, "url_path": "/blog/iris-murdoch/"}},
        ],
    }
    route = respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "pages", "find", "murdoch"])
    assert result.exit_code == 0
    assert "Iris Murdoch" in result.output
    assert "search" in str(route.calls[0].request.url)


@respx.mock
def test_pages_find_with_type(runner):
    """Find accepts --type filter."""
    data = {"meta": {"total_count": 0}, "items": []}
    route = respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "pages", "find", "test", "--type", "blog.BlogPage"])
    assert result.exit_code == 0
    url = str(route.calls[0].request.url)
    assert "search" in url
    assert "type" in url


@respx.mock
def test_pages_find_no_results(runner):
    """Find with no results shows message."""
    data = {"meta": {"total_count": 0}, "items": []}
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--human", "pages", "find", "nonexistent"])
    assert result.exit_code == 0
    assert "No pages found" in result.output


@respx.mock
def test_pages_find_json(runner):
    """Find with --json returns raw JSON."""
    data = {
        "meta": {"total_count": 1},
        "items": [{"id": 15, "title": "Test", "meta": {"type": "blog.BlogPage", "live": True}}],
    }
    respx.get(f"{BASE_URL}/pages/").mock(return_value=Response(200, json=data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, ["--json", "pages", "find", "test"])
    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert parsed["items"][0]["id"] == 15


# -- block-level update tests --------------------------------------------------


@respx.mock
def test_pages_update_append_block(runner):
    """Append a block to an existing StreamField body."""
    page_data = {
        "id": 42, "title": "Hello",
        "body": [{"type": "paragraph", "value": "<p>old</p>", "id": "aaa"}],
        "meta": {"type": "blog.BlogPage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    updated = {**page_data, "body": page_data["body"] + [{"type": "image", "value": 7, "id": "bbb"}]}
    route = respx.patch(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=updated))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--append-block", '{"type":"image","value":7}',
        ])
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert len(request_body["body"]) == 2
    assert request_body["body"][0]["id"] == "aaa"
    assert request_body["body"][1]["type"] == "image"
    assert "id" in request_body["body"][1]  # UUID generated


@respx.mock
def test_pages_update_insert_block(runner):
    """Insert a block at a specific index."""
    page_data = {
        "id": 42, "title": "Hello",
        "body": [
            {"type": "heading", "value": {"text": "Title", "size": "h1"}, "id": "aaa"},
            {"type": "paragraph", "value": "<p>text</p>", "id": "bbb"},
        ],
        "meta": {"type": "blog.BlogPage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    route = respx.patch(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--insert-block", "1", '{"type":"image","value":5}',
        ])
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert len(request_body["body"]) == 3
    assert request_body["body"][0]["id"] == "aaa"
    assert request_body["body"][1]["type"] == "image"
    assert request_body["body"][2]["id"] == "bbb"


@respx.mock
def test_pages_update_append_multiple_blocks(runner):
    """Multiple --append-block flags append in order."""
    page_data = {
        "id": 42, "title": "Hello", "body": [],
        "meta": {"type": "blog.BlogPage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    route = respx.patch(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--append-block", '{"type":"heading","value":{"text":"Hi","size":"h1"}}',
            "--append-block", '{"type":"paragraph","value":"<p>body</p>"}',
        ])
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert len(request_body["body"]) == 2
    assert request_body["body"][0]["type"] == "heading"
    assert request_body["body"][1]["type"] == "paragraph"


def test_pages_update_block_ops_with_body_error(runner):
    """Cannot use --append-block together with --body."""
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--body", "hello",
            "--append-block", '{"type":"paragraph","value":"<p>x</p>"}',
        ])
    assert result.exit_code != 0
    assert "Cannot use" in result.output


@respx.mock
def test_pages_update_append_block_non_streamfield_error(runner):
    """Error when body is not a StreamField (list)."""
    page_data = {
        "id": 42, "title": "Hello", "body": "<p>richtext</p>",
        "meta": {"type": "home.SimplePage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--append-block", '{"type":"paragraph","value":"<p>x</p>"}',
        ])
    assert result.exit_code != 0
    assert "not a StreamField" in result.output


@respx.mock
def test_pages_update_insert_block_out_of_range(runner):
    """Error when insert index is out of range."""
    page_data = {
        "id": 42, "title": "Hello",
        "body": [{"type": "paragraph", "value": "<p>only</p>", "id": "aaa"}],
        "meta": {"type": "blog.BlogPage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--insert-block", "5", '{"type":"paragraph","value":"<p>x</p>"}',
        ])
    assert result.exit_code != 0
    assert "out of range" in result.output


@respx.mock
def test_pages_update_append_block_invalid_json(runner):
    """Error on invalid JSON in --append-block."""
    page_data = {
        "id": 42, "title": "Hello", "body": [],
        "meta": {"type": "blog.BlogPage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--append-block", "not json",
        ])
    assert result.exit_code != 0
    assert "Invalid JSON" in result.output


@respx.mock
def test_pages_update_append_preserves_existing_id(runner):
    """Block with an existing id keeps it (no override)."""
    page_data = {
        "id": 42, "title": "Hello", "body": [],
        "meta": {"type": "blog.BlogPage", "live": True},
    }
    respx.get(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    route = respx.patch(f"{BASE_URL}/pages/42/").mock(return_value=Response(200, json=page_data))
    with mock.patch.dict("os.environ", ENV):
        result = runner.invoke(cli, [
            "pages", "update", "42",
            "--append-block", '{"type":"image","value":3,"id":"keep-me"}',
        ])
    assert result.exit_code == 0
    request_body = json.loads(route.calls[0].request.content)
    assert request_body["body"][0]["id"] == "keep-me"


# -- images upload tests -------------------------------------------------------


@respx.mock
def test_images_upload(runner):
    """Upload an image file."""
    data = {"id": 10, "title": "photo", "width": 800, "height": 600, "meta": {}}
    respx.post(f"{BASE_URL}/images/").mock(return_value=Response(201, json=data))
    with runner.isolated_filesystem():
        with open("photo.png", "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        with mock.patch.dict("os.environ", ENV):
            result = runner.invoke(cli, ["--human", "images", "upload", "photo.png"])
    assert result.exit_code == 0
    assert "Uploaded" in result.output
    assert "photo" in result.output


@respx.mock
def test_images_upload_default_title(runner):
    """Upload without --title uses filename stem."""
    data = {"id": 11, "title": "my_photo", "width": 100, "height": 100, "meta": {}}
    route = respx.post(f"{BASE_URL}/images/").mock(return_value=Response(201, json=data))
    with runner.isolated_filesystem():
        with open("my_photo.jpg", "wb") as f:
            f.write(b"\xff\xd8" + b"\x00" * 50)
        with mock.patch.dict("os.environ", ENV):
            result = runner.invoke(cli, ["--human", "images", "upload", "my_photo.jpg"])
    assert result.exit_code == 0
    # Check form data includes filename-derived title
    request = route.calls[0].request
    assert b"my_photo" in request.content


@respx.mock
def test_images_upload_custom_title(runner):
    """Upload with --title uses the provided title."""
    data = {"id": 12, "title": "My Photo", "width": 100, "height": 100, "meta": {}}
    route = respx.post(f"{BASE_URL}/images/").mock(return_value=Response(201, json=data))
    with runner.isolated_filesystem():
        with open("img.png", "wb") as f:
            f.write(b"\x89PNG" + b"\x00" * 50)
        with mock.patch.dict("os.environ", ENV):
            result = runner.invoke(cli, ["--human", "images", "upload", "img.png", "--title", "My Photo"])
    assert result.exit_code == 0
    request = route.calls[0].request
    assert b"My Photo" in request.content
