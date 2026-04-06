from __future__ import annotations

import click

from wagapi.cli import Context, handle_api_errors, pass_ctx
from wagapi.exceptions import UsageError
from wagapi.formatting.output import (
    format_json,
    format_schema_detail,
    format_schema_list,
    output,
)


@click.command()
@click.argument("page_type", required=False, default=None)
@pass_ctx
@handle_api_errors
def schema(ctx: Context, page_type: str | None) -> None:
    """List page types, or show the schema for a specific type."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    if page_type:
        data = ctx.client.get_page_type_schema(page_type)
        result = output(
            data,
            format_schema_detail,
            force_json=ctx.force_json,
            force_human=ctx.force_human,
        )
    else:
        data = ctx.client.list_page_types()
        result = output(
            data,
            format_schema_list,
            force_json=ctx.force_json,
            force_human=ctx.force_human,
        )

    click.echo(result)
