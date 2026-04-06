from __future__ import annotations

import re
import uuid

from markdown_it import MarkdownIt


def _make_id() -> str:
    return str(uuid.uuid4())


def markdown_to_streamfield(text: str) -> list[dict]:
    """Convert markdown text to a list of StreamField block dicts.

    Conversion rules:
    - # Heading  → {"type": "heading", "value": {"text": "...", "size": "h1"}, "id": "..."}
    - ## Heading → h2, ### Heading → h3
    - Paragraphs → {"type": "paragraph", "value": {"format": "markdown", "content": "..."}, "id": "..."}
    - ![alt](wagapi:image/42) → {"type": "image", "value": 42, "id": "..."}
    """
    md = MarkdownIt("commonmark")
    tokens = md.parse(text)

    blocks: list[dict] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]

        if tok.type == "heading_open":
            level = tok.tag  # h1, h2, h3, etc.
            # Next token is the heading inline content
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                heading_text = tokens[i + 1].content
                blocks.append({
                    "type": "heading",
                    "value": {"text": heading_text, "size": level},
                    "id": _make_id(),
                })
                i += 3  # skip heading_open, inline, heading_close
                continue

        if tok.type == "paragraph_open":
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                inline_content = tokens[i + 1].content

                # Check if this paragraph is a standalone image reference
                image_match = re.fullmatch(
                    r"!\[([^\]]*)\]\(wagapi:image/(\d+)\)", inline_content
                )
                if image_match:
                    image_id = int(image_match.group(2))
                    blocks.append({
                        "type": "image",
                        "value": image_id,
                        "id": _make_id(),
                    })
                    i += 3  # skip paragraph_open, inline, paragraph_close
                    continue

                # Regular paragraph — keep as markdown
                blocks.append({
                    "type": "paragraph",
                    "value": {
                        "format": "markdown",
                        "content": inline_content,
                    },
                    "id": _make_id(),
                })
                i += 3
                continue

        # Skip tokens we don't handle (fences, lists, etc.)
        i += 1

    return blocks


def markdown_to_richtext(text: str) -> dict:
    """Convert markdown text to a RichTextField value."""
    return {"format": "markdown", "content": text}
