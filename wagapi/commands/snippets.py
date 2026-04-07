from __future__ import annotations

import sys

import click

from wagapi.cli import Context, handle_api_errors, pass_ctx
from wagapi.commands.pages import _parse_fields
from wagapi.exceptions import UsageError
from wagapi.formatting.output import (
    format_snippet_created,
    format_snippet_deleted,
    format_snippet_detail,
    format_snippet_list,
    format_snippet_updated,
    output,
)


@click.group()
def snippets():
    """Manage snippets."""
    pass


@snippets.command("list")
@click.argument("snippet_type")
@click.option("--search", default=None, help="Search by name/title")
@click.option("--limit", default=None, type=int, help="Items per page")
@click.option("--offset", default=None, type=int, help="Pagination offset")
@pass_ctx
@handle_api_errors
def list_snippets(ctx: Context, snippet_type, search, limit, offset):
    """List snippets of a given type."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    params = {}
    if search:
        params["search"] = search
    if limit is not None:
        params["limit"] = limit
    if offset is not None:
        params["offset"] = offset

    data = ctx.client.list_snippets(snippet_type, **params)
    result = output(
        data,
        format_snippet_list,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@snippets.command()
@click.argument("snippet_type")
@click.argument("snippet_id", type=int)
@pass_ctx
@handle_api_errors
def get(ctx: Context, snippet_type: str, snippet_id: int):
    """Get snippet detail."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    data = ctx.client.get_snippet(snippet_type, snippet_id)
    result = output(
        data,
        format_snippet_detail,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@snippets.command()
@click.argument("snippet_type")
@click.option("--field", "fields", multiple=True, help="Set field value as KEY:VALUE (repeatable)")
@click.option("--raw", is_flag=True, help="Treat all field values as raw JSON")
@pass_ctx
@handle_api_errors
def create(ctx: Context, snippet_type, fields, raw):
    """Create a new snippet."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    data = {"type": snippet_type}
    field_data = _parse_fields(fields, raw)
    data.update(field_data)

    result_data = ctx.client.create_snippet(data)
    if result_data is None:
        return
    result = output(
        result_data,
        format_snippet_created,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@snippets.command()
@click.argument("snippet_type")
@click.argument("snippet_id", type=int)
@click.option("--field", "fields", multiple=True, help="Set field value as KEY:VALUE (repeatable)")
@click.option("--raw", is_flag=True, help="Treat all field values as raw JSON")
@pass_ctx
@handle_api_errors
def update(ctx: Context, snippet_type, snippet_id, fields, raw):
    """Update a snippet."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    field_data = _parse_fields(fields, raw)
    if not field_data:
        raise UsageError("No fields to update. Use --field KEY:VALUE.")

    result_data = ctx.client.update_snippet(snippet_type, snippet_id, field_data)
    if result_data is None:
        return
    result = output(
        result_data,
        format_snippet_updated,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@snippets.command()
@click.argument("snippet_type")
@click.argument("snippet_id", type=int)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
@pass_ctx
@handle_api_errors
def delete(ctx: Context, snippet_type, snippet_id, yes):
    """Delete a snippet."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    if not yes and sys.stdout.isatty():
        click.confirm(f"Delete {snippet_type} {snippet_id}?", abort=True)

    ctx.client.delete_snippet(snippet_type, snippet_id)
    result = output(
        {"id": snippet_id, "type": snippet_type, "deleted": True},
        format_snippet_deleted,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)
