from __future__ import annotations

import click

from wagapi.cli import Context, handle_api_errors, pass_ctx
from wagapi.client import WagtailClient
from wagapi.config import USER_CONFIG_PATH, write_config


@click.command()
@click.option("--url", default=None, help="Wagtail Write API URL")
@click.option("--token", default=None, help="API token")
@pass_ctx
@handle_api_errors
def init(ctx: Context, url: str | None, token: str | None) -> None:
    """Configure wagapi connection settings."""
    if not url:
        url = click.prompt("Wagtail Write API URL")
    if not token:
        token = click.prompt("API Token", hide_input=True)

    # Test connection
    click.echo("Testing connection... ", nl=False)
    client = WagtailClient(url, token)
    try:
        page_types = client.list_page_types()
        count = len(page_types)
        click.echo(f"✓ Connected ({count} page type{'s' if count != 1 else ''} found)")
    except Exception as exc:
        click.echo(f"✗ Failed: {exc}", err=True)
        raise click.Abort()
    finally:
        client.close()

    # Write config
    write_config(USER_CONFIG_PATH, url, token)
    click.echo(f"Config written to {USER_CONFIG_PATH}")
    click.echo()
    click.echo(
        "Tip: for CI or shared machines, use WAGAPI_URL and WAGAPI_TOKEN\n"
        "environment variables instead."
    )
