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


def _build_example_command(page_type: str, data: dict) -> str:
    """Generate an example wagapi create command from schema data."""
    create_schema = data.get("create_schema", {})
    properties = create_schema.get("properties", {})
    required = set(create_schema.get("required", []))
    has_streamfield = bool(data.get("streamfield_blocks"))

    # CLI handles type and parent itself; action is internal
    skip = {"type", "parent", "action"}

    parts = [f"wagapi pages create {page_type}", "--parent <ID_OR_PATH>"]

    for field_name in properties:
        if field_name in skip:
            continue
        if field_name not in required:
            continue
        prop = properties[field_name]

        # StreamField body → use --body flag
        if field_name == "body" and prop.get("type") == "array":
            parts.append('--body "Your content here (markdown)"')
            continue

        # Derive a placeholder from the field type
        ftype = prop.get("type", "")
        if ftype == "string":
            parts.append(f'--field {field_name}:"..."')
        elif ftype == "integer":
            parts.append(f"--field {field_name}:<ID>")
        elif ftype == "array":
            parts.append(f"--field {field_name}:[]")
        else:
            parts.append(f'--field {field_name}:"..."')

    # title is always a CLI flag, not --field
    parts = [p for p in parts if not p.startswith("--field title:")]
    if "title" in required:
        parts.insert(2, '--title "Your Title"')

    return " \\\n  ".join(parts)


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
        data["example_cli"] = _build_example_command(page_type, data)
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
