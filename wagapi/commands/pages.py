from __future__ import annotations

import json
import sys
import uuid

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
    fields: tuple[str, ...],
    raw: bool,
    streamfield_names: set[str] | None = None,
    richtext_names: set[str] | None = None,
    schema_info: dict | None = None,
) -> dict:
    """Parse --field KEY:VALUE pairs into a dict.

    Values that look like JSON arrays or objects are auto-detected and
    parsed regardless of the ``raw`` flag.  When ``raw`` is True, *all*
    values are attempted as JSON (including bare numbers and strings).

    When ``streamfield_names`` is provided, fields whose key appears in the
    set are auto-converted from markdown to StreamField blocks.  When
    ``richtext_names`` is provided, matching fields are wrapped in the
    richtext format dict.
    """
    result = {}
    for field in fields:
        if ":" not in field:
            raise UsageError(f"Invalid field format '{field}'. Expected KEY:VALUE")
        key, value = field.split(":", 1)
        if raw or (value and value[0] in ("{", "[")):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # keep as string if not valid JSON
        elif streamfield_names and key in streamfield_names:
            blocks = markdown_to_streamfield(value)
            # Apply block remapping if schema_info is available
            if schema_info:
                sf_blocks = schema_info.get("streamfield_blocks", {})
                if key in sf_blocks:
                    block_list = sf_blocks[key]
                    if isinstance(block_list, list):
                        allowed = [b.get("type", b.get("name", "")) for b in block_list]
                    elif isinstance(block_list, dict):
                        allowed = list(block_list.keys())
                    else:
                        allowed = []
                    blocks = _remap_blocks(blocks, allowed)
            value = blocks
        elif richtext_names and key in richtext_names:
            value = markdown_to_richtext(value)
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


def _parse_streamfields(streamfields: tuple[str, ...]) -> dict:
    """Parse --streamfield FIELD:MARKDOWN pairs, converting markdown to blocks."""
    result = {}
    for sf in streamfields:
        if ":" not in sf:
            raise UsageError(f"Invalid streamfield format '{sf}'. Expected FIELD:MARKDOWN")
        key, value = sf.split(":", 1)
        if value == "-":
            value = sys.stdin.read()
        result[key] = markdown_to_streamfield(value)
    return result


@pages.command()
@click.argument("page_type")
@click.option("--parent", required=True, help="Parent page ID or URL path")
@click.option("--title", required=True, help="Page title")
@click.option("--slug", default=None, help="URL slug (auto-generated if omitted)")
@click.option("--field", "fields", multiple=True, help="Set field value as KEY:VALUE (repeatable)")
@click.option(
    "--streamfield", "streamfields", multiple=True,
    help="Set StreamField as FIELD:MARKDOWN (repeatable). Use '-' as value for stdin.",
)
@click.option("--publish", is_flag=True, help="Publish immediately")
@click.option("--raw", is_flag=True, help="Treat field values as raw JSON")
@pass_ctx
@handle_api_errors
def create(ctx: Context, page_type, parent, title, slug, fields, streamfields, publish, raw):
    """Create a new page."""
    _require_client(ctx)

    data: dict = {
        "type": page_type,
        "parent": _parse_parent(parent),
        "title": title,
    }

    if slug:
        data["slug"] = slug

    # Fetch schema for auto-detection when there are --field values and not --raw
    streamfield_names = None
    richtext_names = None
    schema_info = None
    if fields and not raw:
        try:
            schema_info = ctx.client.get_page_type_schema(page_type)
            streamfield_names = set(schema_info.get("streamfield_blocks", {}).keys())
            richtext_names = set(schema_info.get("richtext_fields", []))
        except Exception:
            pass  # schema lookup failed, skip auto-detection

    # Parse --field options (with auto-detection)
    field_data = _parse_fields(fields, raw, streamfield_names, richtext_names, schema_info)
    data.update(field_data)

    # Parse --streamfield options (explicit, no schema needed)
    sf_data = _parse_streamfields(streamfields)
    data.update(sf_data)

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
@click.option("--type", "page_type", default=None, help="Page type (enables auto StreamField detection)")
@click.option("--field", "fields", multiple=True, help="Set field value as KEY:VALUE (repeatable)")
@click.option(
    "--streamfield", "streamfields", multiple=True,
    help="Set StreamField as FIELD:MARKDOWN (repeatable). Use '-' as value for stdin.",
)
@click.option("--publish", is_flag=True, help="Publish after update")
@click.option("--raw", is_flag=True, help="Treat field values as raw JSON")
@click.option(
    "--append-block", "append_blocks", multiple=True,
    help="Append a JSON block to body StreamField (repeatable).",
)
@click.option(
    "--insert-block", "insert_blocks", nargs=2, multiple=True,
    metavar="INDEX JSON",
    help="Insert a JSON block at INDEX in body StreamField (repeatable).",
)
@pass_ctx
@handle_api_errors
def update(ctx: Context, page_id, title, slug, page_type, fields, streamfields,
           publish, raw, append_blocks, insert_blocks):
    """Update an existing page (PATCH semantics).

    Use --append-block or --insert-block to add blocks to an existing
    StreamField body without replacing the whole thing. These flags fetch the
    current body, splice in the new block(s), and send the result.

    \b
    Examples:
      wagapi pages update 42 --field "body:## New content"
      wagapi pages update 42 --append-block '{"type":"image","value":7}'
      wagapi pages update 42 --insert-block 1 '{"type":"paragraph","value":"<p>New</p>"}'
    """
    _require_client(ctx)

    data: dict = {}

    if title:
        data["title"] = title
    if slug:
        data["slug"] = slug

    # Fetch schema for auto-detection when there are --field values and not --raw
    streamfield_names = None
    richtext_names = None
    schema_info = None
    need_page_fetch = False

    if fields and not raw:
        if page_type:
            # --type provided: fetch schema directly (one request)
            try:
                schema_info = ctx.client.get_page_type_schema(page_type)
                streamfield_names = set(schema_info.get("streamfield_blocks", {}).keys())
                richtext_names = set(schema_info.get("richtext_fields", []))
            except Exception:
                pass
        else:
            # No --type: fetch page to learn type, then fetch schema
            need_page_fetch = True
            try:
                page_data = ctx.client.get_page(page_id)
                page_type = page_data.get("meta", {}).get("type", "")
                if page_type:
                    schema_info = ctx.client.get_page_type_schema(page_type)
                    streamfield_names = set(schema_info.get("streamfield_blocks", {}).keys())
                    richtext_names = set(schema_info.get("richtext_fields", []))
            except Exception:
                pass

    field_data = _parse_fields(fields, raw, streamfield_names, richtext_names, schema_info)
    data.update(field_data)

    # Parse --streamfield options (explicit, no schema needed)
    sf_data = _parse_streamfields(streamfields)
    data.update(sf_data)

    has_block_ops = bool(append_blocks or insert_blocks)

    if has_block_ops:
        # Need to fetch existing body for block operations
        if not need_page_fetch:
            page_data = ctx.client.get_page(page_id)
        existing_body = page_data.get("body")
        if existing_body is None:
            existing_body = []
        if not isinstance(existing_body, list):
            raise UsageError(
                "body field is not a StreamField (not a JSON array). "
                "Use --field instead."
            )
        new_body = list(existing_body)

        # Process inserts (reverse-sort by index to preserve positions)
        parsed_inserts = []
        for idx_str, block_json in insert_blocks:
            try:
                idx = int(idx_str)
            except ValueError:
                raise UsageError(f"Invalid index '{idx_str}' for --insert-block")
            try:
                block = json.loads(block_json)
            except json.JSONDecodeError as e:
                raise UsageError(f"Invalid JSON for --insert-block: {e}")
            if "id" not in block:
                block["id"] = str(uuid.uuid4())
            parsed_inserts.append((idx, block))

        for idx, block in sorted(parsed_inserts, key=lambda x: x[0], reverse=True):
            if idx < 0 or idx > len(new_body):
                raise UsageError(
                    f"Index {idx} out of range (body has {len(new_body)} blocks)"
                )
            new_body.insert(idx, block)

        # Process appends in order
        for block_json in append_blocks:
            try:
                block = json.loads(block_json)
            except json.JSONDecodeError as e:
                raise UsageError(f"Invalid JSON for --append-block: {e}")
            if "id" not in block:
                block["id"] = str(uuid.uuid4())
            new_body.append(block)

        data["body"] = new_body

    if publish:
        data["action"] = "publish"

    if not data:
        raise UsageError("No fields to update. Use --title, --field, --streamfield, --append-block, or --insert-block.")

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
