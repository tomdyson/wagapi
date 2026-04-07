from __future__ import annotations

from wagapi.formatting.markdown import markdown_to_richtext, markdown_to_streamfield


def test_heading_h1():
    blocks = markdown_to_streamfield("# Hello")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "heading"
    assert blocks[0]["value"]["text"] == "Hello"
    assert blocks[0]["value"]["size"] == "h1"
    assert "id" in blocks[0]


def test_heading_h2():
    blocks = markdown_to_streamfield("## Subheading")
    assert len(blocks) == 1
    assert blocks[0]["value"]["size"] == "h2"


def test_heading_h3():
    blocks = markdown_to_streamfield("### Third Level")
    assert len(blocks) == 1
    assert blocks[0]["value"]["size"] == "h3"


def test_paragraph():
    blocks = markdown_to_streamfield("Hello world, this is a paragraph.")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert blocks[0]["value"] == "<p>Hello world, this is a paragraph.</p>"


def test_mixed_headings_and_paragraphs():
    md = """## Early Life

Iris Murdoch was born in Dublin in 1919.

## Philosophy

She argued that moral progress comes from **attention**."""
    blocks = markdown_to_streamfield(md)
    assert len(blocks) == 4
    assert blocks[0]["type"] == "heading"
    assert blocks[0]["value"]["text"] == "Early Life"
    assert blocks[0]["value"]["size"] == "h2"
    assert blocks[1]["type"] == "paragraph"
    assert "Iris Murdoch was born in Dublin in 1919." in blocks[1]["value"]
    assert blocks[2]["type"] == "heading"
    assert blocks[2]["value"]["text"] == "Philosophy"
    assert blocks[3]["type"] == "paragraph"
    assert "<strong>attention</strong>" in blocks[3]["value"]


def test_image_reference():
    blocks = markdown_to_streamfield("![Hero](wagapi:image/42)")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "image"
    assert blocks[0]["value"] == 42


def test_image_mixed_with_text():
    md = """Some intro text.

![Photo](wagapi:image/7)

More text after."""
    blocks = markdown_to_streamfield(md)
    assert len(blocks) == 3
    assert blocks[0]["type"] == "paragraph"
    assert blocks[1]["type"] == "image"
    assert blocks[1]["value"] == 7
    assert blocks[2]["type"] == "paragraph"


def test_unique_ids():
    blocks = markdown_to_streamfield("# One\n\n# Two\n\nParagraph")
    ids = [b["id"] for b in blocks]
    assert len(ids) == len(set(ids)), "Block IDs must be unique"


def test_empty_input():
    blocks = markdown_to_streamfield("")
    assert blocks == []


def test_bullet_list():
    blocks = markdown_to_streamfield("- Alpha\n- Beta\n- Gamma")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert "<ul>" in blocks[0]["value"]
    assert "<li>Alpha</li>" in blocks[0]["value"]
    assert "<li>Gamma</li>" in blocks[0]["value"]


def test_ordered_list():
    blocks = markdown_to_streamfield("1. First\n2. Second\n3. Third")
    assert len(blocks) == 1
    assert blocks[0]["type"] == "paragraph"
    assert "<ol>" in blocks[0]["value"]
    assert "<li>First</li>" in blocks[0]["value"]


def test_list_between_paragraphs():
    md = """Some intro text.

- Item one
- Item two

Closing paragraph."""
    blocks = markdown_to_streamfield(md)
    assert len(blocks) == 3
    assert blocks[0]["type"] == "paragraph"
    assert "intro" in blocks[0]["value"]
    assert blocks[1]["type"] == "paragraph"
    assert "<ul>" in blocks[1]["value"]
    assert blocks[2]["type"] == "paragraph"
    assert "Closing" in blocks[2]["value"]


def test_markdown_to_richtext():
    result = markdown_to_richtext("Hello **world**")
    assert result == {"format": "markdown", "content": "Hello **world**"}
