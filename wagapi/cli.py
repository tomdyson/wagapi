from __future__ import annotations

import sys
from functools import wraps
from typing import Any

import click

from wagapi.client import WagtailClient
from wagapi.config import load_config
from wagapi.exceptions import WagapiError


class Context:
    """Shared state passed through click context."""

    def __init__(self) -> None:
        self.client: WagtailClient | None = None
        self.force_json: bool = False
        self.force_human: bool = False
        self.verbose: bool = False
        self.dry_run: bool = False


pass_ctx = click.make_pass_decorator(Context, ensure=True)


def handle_api_errors(fn):
    """Decorator that catches WagapiError and exits with the right code."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except WagapiError as exc:
            click.echo(f"Error: {exc}", err=True)
            if hasattr(exc, "details") and exc.details:
                click.echo(f"Details: {exc.details}", err=True)
            sys.exit(exc.exit_code)

    return wrapper


@click.group()
@click.option("--url", envvar="WAGAPI_URL", default=None, help="API base URL")
@click.option("--token", envvar="WAGAPI_TOKEN", default=None, help="API token")
@click.option("--json", "output_json", is_flag=True, help="Force JSON output")
@click.option("--human", "output_human", is_flag=True, help="Force human-readable output")
@click.option("-v", "--verbose", is_flag=True, help="Print HTTP details to stderr")
@click.option("--dry-run", is_flag=True, help="Print request without executing")
@click.pass_context
def cli(ctx: click.Context, url, token, output_json, output_human, verbose, dry_run):
    """wagapi — CLI client for the Wagtail Write API."""
    obj = Context()
    obj.force_json = output_json
    obj.force_human = output_human
    obj.verbose = verbose
    obj.dry_run = dry_run
    ctx.ensure_object(dict)
    ctx.obj = obj

    # Load config (merging CLI flags, env vars, dotfiles)
    config = load_config(cli_url=url, cli_token=token)

    if config.is_configured:
        obj.client = WagtailClient(config.url, config.token, verbose=obj.verbose, dry_run=obj.dry_run)

    # Store config for commands that need it (e.g. init)
    obj._config = config


# Import and register command groups
from wagapi.commands.init import init  # noqa: E402
from wagapi.commands.schema import schema  # noqa: E402
from wagapi.commands.pages import pages  # noqa: E402
from wagapi.commands.images import images  # noqa: E402

cli.add_command(init)
cli.add_command(schema)
cli.add_command(pages)
cli.add_command(images)
