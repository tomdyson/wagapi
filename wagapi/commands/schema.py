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


def _build_example_command(type_name: str, data: dict, *, is_snippet: bool = False) -> str:
    """Generate an example wagapi create command from schema data."""
    create_schema = data.get("create_schema", {})
    properties = create_schema.get("properties", {})
    required = set(create_schema.get("required", []))

    skip = {"type", "parent", "action"}

    if is_snippet:
        parts = [f"wagapi snippets create {type_name}"]
    else:
        parts = [f"wagapi pages create {type_name}", "--parent <ID_OR_PATH>"]

    for field_name in properties:
        if field_name in skip:
            continue
        if field_name not in required:
            continue
        prop = properties[field_name]

        # StreamField body → use --body flag (pages only)
        if not is_snippet and field_name == "body" and prop.get("type") == "array":
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

    # title is always a CLI flag for pages, not --field
    if not is_snippet:
        parts = [p for p in parts if not p.startswith("--field title:")]
        if "title" in required:
            parts.insert(2, '--title "Your Title"')

    return " \\\n  ".join(parts)


@click.command()
@click.argument("type_name", required=False, default=None)
@click.option("--snippets", "snippets_only", is_flag=True, help="Show only snippet types")
@click.option("--all", "show_all", is_flag=True, help="Show both page and snippet types")
@pass_ctx
@handle_api_errors
def schema(ctx: Context, type_name: str | None, snippets_only: bool, show_all: bool) -> None:
    """List page/snippet types, or show the schema for a specific type."""
    if not ctx.client:
        raise UsageError(
            "Not configured. Run 'wagapi init' or set WAGAPI_URL and WAGAPI_TOKEN."
        )

    if type_name:
        # Detail view for a single type
        is_snippet = False
        if snippets_only:
            data = ctx.client.get_snippet_type_schema(type_name)
            is_snippet = True
        else:
            try:
                data = ctx.client.get_page_type_schema(type_name)
            except Exception:
                data = ctx.client.get_snippet_type_schema(type_name)
                is_snippet = True
        data["example_cli"] = _build_example_command(type_name, data, is_snippet=is_snippet)
        result = output(
            data,
            format_schema_detail,
            force_json=ctx.force_json,
            force_human=ctx.force_human,
        )
        click.echo(result)
    elif snippets_only:
        data = ctx.client.list_snippet_types()
        result = output(
            data,
            format_schema_list,
            force_json=ctx.force_json,
            force_human=ctx.force_human,
        )
        click.echo(result)
    elif show_all:
        page_data = ctx.client.list_page_types()
        result = output(
            page_data,
            format_schema_list,
            force_json=ctx.force_json,
            force_human=ctx.force_human,
        )
        click.echo(result)
        snippet_data = ctx.client.list_snippet_types()
        if snippet_data:
            click.echo()
            result = output(
                snippet_data,
                format_schema_list,
                force_json=ctx.force_json,
                force_human=ctx.force_human,
            )
            click.echo(result)
    else:
        # Default: page types only (backward compatible)
        data = ctx.client.list_page_types()
        result = output(
            data,
            format_schema_list,
            force_json=ctx.force_json,
            force_human=ctx.force_human,
        )
        click.echo(result)
