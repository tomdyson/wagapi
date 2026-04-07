from __future__ import annotations

import json
import sys

import click

from wagapi.cli import Context, handle_api_errors, pass_ctx
from wagapi.exceptions import NotFoundError, UsageError
from wagapi.formatting.markdown import markdown_to_richtext, markdown_to_streamfield
from wagapi.formatting.output import (
    format_page_created,
    format_page_deleted,
    format_page_detail,
    format_page_find,
    format_page_list,
    format_page_published,
    format_page_unpublished,
    format_page_updated,
    output,
)


def _require_client(ctx: Context):
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )


def _get_streamfield_info(ctx: Context, page_type: str, field_name: str) -> tuple[bool, list[str]]:
    """Check if a field is a StreamField and return (is_streamfield, allowed_block_types)."""
    try:
        schema = ctx.client.get_page_type_schema(page_type)
        sf_blocks = schema.get("streamfield_blocks", {})
        if field_name in sf_blocks:
            blocks = sf_blocks[field_name]
            if isinstance(blocks, list):
                types = [b.get("type", b.get("name", "")) for b in blocks]
            elif isinstance(blocks, dict):
                types = list(blocks.keys())
            else:
                types = []
            return True, types
        return False, []
    except Exception:
        return True, []  # default to StreamField if schema lookup fails


_BLOCK_REMAPS = {
    "paragraph": ["text", "rich_text", "richtext"],
    "heading": ["title", "header"],
}


def _remap_blocks(blocks: list[dict], allowed_types: list[str]) -> list[dict]:
    """Remap block types to match the schema's allowed types."""
    if not allowed_types:
        return blocks  # no schema info, pass through
    allowed = set(allowed_types)
    result = []
    for block in blocks:
        btype = block.get("type", "")
        if btype in allowed:
            result.append(block)
        elif btype in _BLOCK_REMAPS:
            remapped = None
            for alt in _BLOCK_REMAPS[btype]:
                if alt in allowed:
                    remapped = alt
                    break
            if remapped:
                result.append({**block, "type": remapped})
            else:
                click.echo(f"Warning: no remap for block type '{btype}' (allowed: {', '.join(sorted(allowed))})", err=True)
                result.append(block)
        else:
            result.append(block)
    return result


def _parse_parent(value: str) -> int | str:
    """Parse parent as int ID or string path."""
    try:
        return int(value)
    except ValueError:
        return value


def _parse_fields(
    fields: tuple[str, ...], raw: bool
) -> dict:
    """Parse --field KEY:VALUE pairs into a dict."""
    result = {}
    for field in fields:
        if ":" not in field:
            raise UsageError(f"Invalid field format '{field}'. Expected KEY:VALUE")
        key, value = field.split(":", 1)
        if raw:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # keep as string if not valid JSON
        result[key] = value
    return result


@click.group()
def pages():
    """Manage pages."""
    pass


@pages.command("list")
@click.option("--type", "page_type", default=None, help="Filter by page type")
@click.option("--parent", default=None, help="Direct children of page ID")
@click.option("--descendant-of", default=None, help="All descendants of page ID")
@click.option("--status", default=None, help="draft, live, or live+draft")
@click.option("--slug", default=None, help="Exact slug match")
@click.option("--path", default=None, help="Exact URL path match")
@click.option("--search", default=None, help="Full-text search")
@click.option("--order", default=None, help="Sort field")
@click.option("--limit", default=None, type=int, help="Items per page (default: 20)")
@click.option("--offset", default=None, type=int, help="Pagination offset")
@pass_ctx
@handle_api_errors
def list_pages(
    ctx: Context,
    page_type,
    parent,
    descendant_of,
    status,
    slug,
    path,
    search,
    order,
    limit,
    offset,
):
    """List pages with optional filters."""
    _require_client(ctx)
    params = {}
    if page_type:
        params["type"] = page_type
    if parent:
        params["parent"] = parent
    if descendant_of:
        params["descendant_of"] = descendant_of
    if status:
        params["status"] = status
    if slug:
        params["slug"] = slug
    if path:
        params["path"] = path
    if search:
        params["search"] = search
    if order:
        params["order"] = order
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    data = ctx.client.list_pages(**params)
    result = output(
        data,
        format_page_list,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("query")
@click.option("--type", "page_type", default=None, help="Filter by page type")
@pass_ctx
@handle_api_errors
def find(ctx: Context, query: str, page_type: str | None):
    """Search for pages by title or content."""
    _require_client(ctx)
    params = {"search": query}
    if page_type:
        params["type"] = page_type
    data = ctx.client.list_pages(**params)
    result = output(
        data,
        format_page_find,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("page_id")
@click.option("--version", default=None, help="Version to retrieve (e.g. 'live')")
@pass_ctx
@handle_api_errors
def get(ctx: Context, page_id: str, version: str | None):
    """Get page detail by ID or URL path."""
    _require_client(ctx)
    if page_id.startswith("/"):
        results = ctx.client.list_pages(path=page_id)
        items = results.get("items", results.get("results", []))
        if not items:
            raise NotFoundError(f"No page found at path: {page_id}")
        page_id = items[0]["id"]
    else:
        page_id = int(page_id)
    data = ctx.client.get_page(page_id, version=version)
    result = output(
        data,
        format_page_detail,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("page_type")
@click.option("--parent", required=True, help="Parent page ID or URL path")
@click.option("--title", required=True, help="Page title")
@click.option("--slug", default=None, help="URL slug (auto-generated if omitted)")
@click.option("--field", "fields", multiple=True, help="Set field value as KEY:VALUE (repeatable)")
@click.option("--body", default=None, help="Body content (markdown). Use '-' for stdin.")
@click.option("--publish", is_flag=True, help="Publish immediately")
@click.option("--raw", is_flag=True, help="Treat field values as raw JSON")
@pass_ctx
@handle_api_errors
def create(ctx: Context, page_type, parent, title, slug, fields, body, publish, raw):
    """Create a new page."""
    _require_client(ctx)

    data: dict = {
        "type": page_type,
        "parent": _parse_parent(parent),
        "title": title,
    }

    if slug:
        data["slug"] = slug

    # Parse --field options
    field_data = _parse_fields(fields, raw)
    data.update(field_data)

    # Handle --body
    if body is not None:
        if body == "-":
            body = sys.stdin.read()
        if raw:
            try:
                data["body"] = json.loads(body)
            except json.JSONDecodeError:
                data["body"] = body
        else:
            is_sf, allowed_types = _get_streamfield_info(ctx, page_type, "body")
            if is_sf:
                data["body"] = _remap_blocks(markdown_to_streamfield(body), allowed_types)
            else:
                data["body"] = markdown_to_richtext(body)

    if publish:
        data["action"] = "publish"

    result_data = ctx.client.create_page(data)
    if result_data is None:
        return
    result = output(
        result_data,
        format_page_created,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("page_id", type=int)
@click.option("--title", default=None, help="Page title")
@click.option("--slug", default=None, help="URL slug")
@click.option("--field", "fields", multiple=True, help="Set field value as KEY:VALUE (repeatable)")
@click.option("--body", default=None, help="Body content (markdown). Use '-' for stdin.")
@click.option("--publish", is_flag=True, help="Publish after update")
@click.option("--raw", is_flag=True, help="Treat field values as raw JSON")
@pass_ctx
@handle_api_errors
def update(ctx: Context, page_id, title, slug, fields, body, publish, raw):
    """Update an existing page (PATCH semantics)."""
    _require_client(ctx)

    data: dict = {}

    if title:
        data["title"] = title
    if slug:
        data["slug"] = slug

    field_data = _parse_fields(fields, raw)
    data.update(field_data)

    if body is not None:
        if body == "-":
            body = sys.stdin.read()
        if raw:
            try:
                data["body"] = json.loads(body)
            except json.JSONDecodeError:
                data["body"] = body
        else:
            # Fetch page to determine its type, then check schema
            page_data = ctx.client.get_page(page_id)
            page_type = page_data.get("meta", {}).get("type", "")
            is_sf, allowed_types = _get_streamfield_info(ctx, page_type, "body")
            if is_sf:
                data["body"] = _remap_blocks(markdown_to_streamfield(body), allowed_types)
            else:
                data["body"] = markdown_to_richtext(body)

    if publish:
        data["action"] = "publish"

    if not data:
        raise UsageError("No fields to update. Use --title, --field, or --body.")

    result_data = ctx.client.update_page(page_id, data)
    if result_data is None:
        return
    result = output(
        result_data,
        format_page_updated,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("page_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_ctx
@handle_api_errors
def delete(ctx: Context, page_id: int, yes: bool):
    """Delete a page."""
    _require_client(ctx)

    if not yes and sys.stdout.isatty():
        click.confirm(f"Delete page {page_id}?", abort=True)

    ctx.client.delete_page(page_id)
    result = output(
        {"id": page_id, "deleted": True},
        format_page_deleted,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("page_id", type=int)
@pass_ctx
@handle_api_errors
def publish(ctx: Context, page_id: int):
    """Publish a page."""
    _require_client(ctx)
    data = ctx.client.publish_page(page_id)
    if data is None:
        data = {"id": page_id}
    result = output(
        data,
        format_page_published,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@pages.command()
@click.argument("page_id", type=int)
@pass_ctx
@handle_api_errors
def unpublish(ctx: Context, page_id: int):
    """Unpublish a page (revert to draft)."""
    _require_client(ctx)
    data = ctx.client.unpublish_page(page_id)
    if data is None:
        data = {"id": page_id}
    result = output(
        data,
        format_page_unpublished,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)
