from __future__ import annotations

import click

from wagapi.cli import Context, handle_api_errors, pass_ctx
from wagapi.exceptions import UsageError
from wagapi.formatting.output import (
    format_image_detail,
    format_image_list,
    output,
)


@click.group()
def images():
    """Manage images."""
    pass


@images.command("list")
@click.option("--search", default=None, help="Search by title")
@click.option("--limit", default=None, type=int, help="Items per page")
@click.option("--offset", default=None, type=int, help="Pagination offset")
@pass_ctx
@handle_api_errors
def list_images(ctx: Context, search, limit, offset):
    """List images."""
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

    data = ctx.client.list_images(**params)
    result = output(
        data,
        format_image_list,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)


@images.command()
@click.argument("image_id", type=int)
@pass_ctx
@handle_api_errors
def get(ctx: Context, image_id: int):
    """Get image detail."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    data = ctx.client.get_image(image_id)
    result = output(
        data,
        format_image_detail,
        force_json=ctx.force_json,
        force_human=ctx.force_human,
    )
    click.echo(result)
