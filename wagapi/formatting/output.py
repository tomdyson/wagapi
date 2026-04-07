from __future__ import annotations

import json
import sys
from typing import Any, Callable


def is_tty() -> bool:
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()


def format_json(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def output(
    data: Any,
    human_formatter: Callable[[Any], str],
    *,
    force_json: bool = False,
    force_human: bool = False,
) -> str:
    """Return formatted output string, auto-detecting TTY vs pipe."""
    if force_json:
        return format_json(data)
    if force_human:
        return human_formatter(data)
    if is_tty():
        return human_formatter(data)
    return format_json(data)


# -- Human formatters --------------------------------------------------------


def format_page_created(data: dict) -> str:
    meta = data.get("meta", {})
    status = "live" if meta.get("live") else "draft"
    lines = [
        f'✓ Created page {data["id"]} "{data.get("title", "")}" ({status})',
        f'  Type: {meta.get("type", "unknown")}',
    ]
    if meta.get("parent_id"):
        lines.append(f'  Parent: {meta["parent_id"]}')
    if data.get("meta", {}).get("html_url"):
        lines.append(f'  URL: {meta["html_url"]}')
    return "\n".join(lines)


def format_page_updated(data: dict) -> str:
    meta = data.get("meta", {})
    status = "live" if meta.get("live") else "draft"
    return f'✓ Updated page {data["id"]} "{data.get("title", "")}" ({status})'


def format_page_deleted(data: dict) -> str:
    return f'✓ Deleted page {data["id"]}'


def format_page_published(data: dict) -> str:
    return f'✓ Published page {data.get("id", "?")} "{data.get("title", "")}"'


def format_page_unpublished(data: dict) -> str:
    return f'✓ Unpublished page {data.get("id", "?")} "{data.get("title", "")}"'


def _streamfield_preview(blocks: list[dict], max_len: int = 200) -> str:
    """Extract a plain-text preview from StreamField blocks."""
    import re

    parts = []
    for block in blocks:
        btype = block.get("type", "")
        val = block.get("value", "")
        if btype == "heading":
            text = val.get("text", "") if isinstance(val, dict) else str(val)
            parts.append(text)
        elif btype in ("paragraph", "text"):
            text = re.sub(r"<[^>]+>", "", str(val))
            parts.append(text)
    preview = " / ".join(parts)
    if len(preview) > max_len:
        preview = preview[: max_len - 1] + "…"
    return preview


def _richtext_preview(html: str, max_len: int = 200) -> str:
    """Extract a plain-text preview from HTML rich text."""
    import re

    text = re.sub(r"<[^>]+>", "", str(html)).strip()
    if len(text) > max_len:
        text = text[: max_len - 1] + "…"
    return text


def format_page_detail(data: dict) -> str:
    meta = data.get("meta", {})
    status = "live" if meta.get("live") else "draft"
    lines = [
        f'{data.get("title", "Untitled")} (ID: {data["id"]}, {status})',
        f'  Type: {meta.get("type", "unknown")}',
        f'  Slug: {data.get("slug", "")}',
    ]
    if meta.get("url_path"):
        lines.append(f'  Path: {meta["url_path"]}')
    elif meta.get("html_url"):
        lines.append(f'  URL: {meta["html_url"]}')
    if meta.get("parent_id"):
        lines.append(f'  Parent: {meta["parent_id"]}')

    # Show custom fields (skip meta, id, title, slug which are already shown)
    skip = {"id", "title", "slug", "meta", "alias_of"}
    for key, value in data.items():
        if key in skip or value is None:
            continue
        if isinstance(value, list) and value and isinstance(value[0], dict) and "type" in value[0]:
            # StreamField — show preview
            preview = _streamfield_preview(value)
            if preview:
                lines.append(f"  {key}: {preview}")
            else:
                block_types = [b.get("type", "?") for b in value]
                lines.append(f"  {key}: [{', '.join(block_types)}] ({len(value)} blocks)")
        elif isinstance(value, list) and value:
            lines.append(f"  {key}: {len(value)} items")
        elif isinstance(value, list):
            lines.append(f"  {key}: (empty)")
        elif isinstance(value, str) and value and value.startswith("<"):
            # RichTextField HTML — show preview
            lines.append(f"  {key}: {_richtext_preview(value)}")
        else:
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def format_page_list(data: dict) -> str:
    items = data.get("items", data.get("results", []))
    if not items:
        return "No pages found."
    lines = []
    for page in items:
        meta = page.get("meta", {})
        status = "live" if meta.get("live") else "draft"
        url_path = meta.get("url_path", "")
        path_col = f"  {url_path}" if url_path else ""
        lines.append(
            f'  {page["id"]:>5}  {page.get("title", "Untitled"):<40}  '
            f'{meta.get("type", ""):<30}  {status}{path_col}'
        )
    total = data.get("meta", {}).get("total_count", len(items))
    header = f"Pages ({total} total):\n"
    return header + "\n".join(lines)


def format_page_find(data: dict) -> str:
    items = data.get("items", data.get("results", []))
    if not items:
        return "No pages found."
    lines = []
    for page in items:
        meta = page.get("meta", {})
        path = meta.get("url_path", "")
        lines.append(f'  {page["id"]:>5}  {page.get("title", "Untitled"):<40}  {path}')
    return "\n".join(lines)


def format_schema_list(data: list[dict]) -> str:
    if not data:
        return "No page types found."
    lines = []
    for pt in data:
        name = pt.get("type", pt.get("name", pt.get("id", "unknown")))
        label = pt.get("verbose_name", pt.get("label", ""))
        fields = ", ".join(pt.get("fields_summary", pt.get("fields", [])))
        parents = ", ".join(pt.get("allowed_parent_types", pt.get("allowed_parents", [])))
        children = ", ".join(pt.get("allowed_subpage_types", pt.get("allowed_children", [])))
        line = f'{name:<35} — "{label}"'
        if fields:
            line += f"\n  Fields: {fields}"
        if parents:
            line += f"\n  Parents: {parents}"
        if children:
            line += f"\n  Children: {children}"
        else:
            line += "\n  Children: (none)"
        lines.append(line)
    return "\n\n".join(lines)


def format_schema_detail(data: dict) -> str:
    name = data.get("type", data.get("name", data.get("id", "unknown")))
    label = data.get("verbose_name", data.get("label", ""))
    header = f'{name} — "{label}"' if label else name
    lines = [header, ""]

    create_schema = data.get("create_schema", {})
    properties = create_schema.get("properties", {})
    required_fields = set(create_schema.get("required", []))

    streamfield_fields = set(data.get("streamfield_blocks", {}).keys())
    richtext_fields = set(data.get("richtext_fields", []))

    if properties:
        req_lines = []
        opt_lines = []
        for field_name, field_schema in properties.items():
            # Handle anyOf type unions (e.g. {"anyOf": [{"type": "string"}, {"type": "null"}]})
            ftype = field_schema.get("type", "")
            if not ftype and "anyOf" in field_schema:
                types = [t.get("type", t.get("format", "")) for t in field_schema["anyOf"] if t.get("type") != "null"]
                ftype = types[0] if types else "unknown"
            ftype = ftype or "unknown"
            # Use Wagtail-specific type names for clarity
            if field_name in streamfield_fields:
                ftype = "StreamField"
            elif field_name in richtext_fields:
                ftype = "RichText"
            desc = field_schema.get("description", field_schema.get("title", ""))
            entry = f"    {field_name:<20} {ftype:<15} {desc}"
            if field_name in required_fields:
                req_lines.append(entry)
            else:
                opt_lines.append(entry)

        if req_lines:
            lines.append("  Required fields:")
            lines.extend(req_lines)
            lines.append("")
        if opt_lines:
            lines.append("  Optional fields:")
            lines.extend(opt_lines)
            lines.append("")

        if req_lines:
            lines.append("  Note: required fields are enforced on publish, not draft creation.")
            lines.append("")

    if data.get("allowed_parent_types", data.get("allowed_parents")):
        parents = data.get("allowed_parent_types", data.get("allowed_parents", []))
        lines.append(f'  Allowed parents: {", ".join(parents)}')
    if data.get("allowed_subpage_types", data.get("allowed_children")):
        children = data.get("allowed_subpage_types", data.get("allowed_children", []))
        lines.append(f'  Allowed children: {", ".join(children)}')
    else:
        lines.append("  Allowed children: (none)")

    if data.get("streamfield_blocks"):
        lines.append("")
        lines.append("  StreamField blocks:")
        for field_name, blocks in data["streamfield_blocks"].items():
            block_names = [b.get("type", b.get("name", "?")) for b in blocks] if isinstance(blocks, list) else list(blocks.keys()) if isinstance(blocks, dict) else []
            lines.append(f"    {field_name}: {', '.join(block_names)}")

    if data.get("example_cli"):
        lines.append("")
        lines.append(f"  Example:\n    {data['example_cli'].replace(chr(10), chr(10) + '    ')}")

    return "\n".join(lines)


def format_image_list(data: dict) -> str:
    items = data.get("items", data.get("results", []))
    if not items:
        return "No images found."
    lines = ["Images:"]
    for img in items:
        title = img.get("title", "Untitled")
        w, h = img.get("width"), img.get("height")
        dims = f"{w}\u00d7{h}" if w and h else ""
        lines.append(f'  {img["id"]:>5}  {title:<30}  {dims}')
    return "\n".join(lines)


def format_image_detail(data: dict) -> str:
    lines = [
        f'{data.get("title", "Untitled")} (ID: {data["id"]})',
    ]
    if data.get("width") and data.get("height"):
        lines.append(f"  Dimensions: {data['width']}x{data['height']}")
    if data.get("meta", {}).get("download_url"):
        lines.append(f'  URL: {data["meta"]["download_url"]}')
    return "\n".join(lines)


def format_image_uploaded(data: dict) -> str:
    lines = [f'✓ Uploaded image {data["id"]} "{data.get("title", "")}"']
    if data.get("width") and data.get("height"):
        lines.append(f"  Dimensions: {data['width']}x{data['height']}")
    if data.get("meta", {}).get("download_url"):
        lines.append(f'  URL: {data["meta"]["download_url"]}')
    return "\n".join(lines)


# -- Snippet formatters ------------------------------------------------------


def format_snippet_list(data: dict) -> str:
    items = data.get("items", [])
    if not items:
        return "No snippets found."
    lines = []
    for s in items:
        meta = s.get("meta", {})
        name = s.get("name", s.get("title", str(s.get("id", "?"))))
        lines.append(f'  {s["id"]:>5}  {name:<30}  {meta.get("type", "")}')
    total = data.get("meta", {}).get("total_count", len(items))
    header = f"Snippets ({total} total):\n"
    return header + "\n".join(lines)


def format_snippet_detail(data: dict) -> str:
    meta = data.get("meta", {})
    skip = {"id", "meta"}
    name = data.get("name", data.get("title", "Snippet"))
    lines = [f"{name} (ID: {data['id']})"]
    if meta.get("type"):
        lines.append(f'  Type: {meta["type"]}')
    for key, value in data.items():
        if key in skip or value is None:
            continue
        lines.append(f"  {key}: {value}")
    return "\n".join(lines)


def format_snippet_created(data: dict) -> str:
    meta = data.get("meta", {})
    name = data.get("name", data.get("title", ""))
    return f'\u2713 Created snippet {data["id"]} "{name}" ({meta.get("type", "unknown")})'


def format_snippet_updated(data: dict) -> str:
    meta = data.get("meta", {})
    name = data.get("name", data.get("title", ""))
    return f'\u2713 Updated snippet {data["id"]} "{name}" ({meta.get("type", "unknown")})'


def format_snippet_deleted(data: dict) -> str:
    return f'\u2713 Deleted snippet {data["id"]} ({data.get("type", "unknown")})'
