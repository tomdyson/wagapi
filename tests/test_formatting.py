"""Tests for wagapi.formatting.output — human-readable formatters."""

from wagapi.formatting.output import (
    _richtext_preview,
    _streamfield_preview,
    format_page_detail,
    format_page_list,
    format_schema_detail,
)


class TestStreamfieldPreview:
    def test_heading_and_paragraph(self):
        blocks = [
            {"type": "heading", "value": {"text": "Hello", "size": "h2"}},
            {"type": "paragraph", "value": "<p>World <b>bold</b></p>"},
        ]
        assert _streamfield_preview(blocks) == "Hello / World bold"

    def test_plain_text_heading(self):
        blocks = [{"type": "heading", "value": "Just text"}]
        assert _streamfield_preview(blocks) == "Just text"

    def test_truncation(self):
        blocks = [{"type": "paragraph", "value": "<p>" + "x" * 300 + "</p>"}]
        result = _streamfield_preview(blocks, max_len=50)
        assert len(result) == 50
        assert result.endswith("…")

    def test_empty_blocks(self):
        assert _streamfield_preview([]) == ""

    def test_unknown_block_types_skipped(self):
        blocks = [{"type": "image", "value": 42}]
        assert _streamfield_preview(blocks) == ""


class TestRichtextPreview:
    def test_strips_html(self):
        assert _richtext_preview("<p>Hello <b>world</b></p>") == "Hello world"

    def test_truncation(self):
        result = _richtext_preview("<p>" + "x" * 300 + "</p>", max_len=50)
        assert len(result) == 50
        assert result.endswith("…")

    def test_empty(self):
        assert _richtext_preview("") == ""


class TestFormatPageList:
    def test_includes_url_path(self):
        data = {
            "meta": {"total_count": 1},
            "items": [
                {
                    "id": 6,
                    "title": "Blog Post",
                    "meta": {
                        "type": "blog.BlogPage",
                        "live": True,
                        "url_path": "/blog/blog-post/",
                    },
                }
            ],
        }
        result = format_page_list(data)
        assert "/blog/blog-post/" in result

    def test_no_url_path_still_works(self):
        data = {
            "meta": {"total_count": 1},
            "items": [
                {
                    "id": 1,
                    "title": "Root",
                    "meta": {"type": "wagtailcore.Page", "live": True},
                }
            ],
        }
        result = format_page_list(data)
        assert "Root" in result


class TestFormatPageDetail:
    def test_shows_url_path(self):
        data = {
            "id": 6,
            "title": "Blog Post",
            "slug": "blog-post",
            "meta": {
                "type": "blog.BlogPage",
                "live": True,
                "url_path": "/blog/blog-post/",
                "parent_id": 5,
            },
        }
        result = format_page_detail(data)
        assert "Path: /blog/blog-post/" in result

    def test_streamfield_body_preview(self):
        data = {
            "id": 6,
            "title": "Post",
            "slug": "post",
            "meta": {"type": "blog.BlogPage", "live": True},
            "body": [
                {"type": "heading", "value": {"text": "Intro", "size": "h2"}},
                {"type": "paragraph", "value": "<p>Some content here.</p>"},
            ],
        }
        result = format_page_detail(data)
        assert "body: Intro / Some content here." in result

    def test_richtext_body_preview(self):
        data = {
            "id": 4,
            "title": "About",
            "slug": "about",
            "meta": {"type": "home.SimplePage", "live": True},
            "body": "<p>About us page content</p>",
        }
        result = format_page_detail(data)
        assert "body: About us page content" in result


class TestFormatSchemaDetail:
    def test_streamfield_type_annotation(self):
        data = {
            "type": "blog.BlogPage",
            "create_schema": {
                "required": ["body"],
                "properties": {
                    "body": {"type": "array", "title": "Body"},
                },
            },
            "streamfield_blocks": {"body": [{"type": "paragraph"}]},
            "richtext_fields": [],
        }
        result = format_schema_detail(data)
        assert "StreamField" in result

    def test_richtext_type_annotation(self):
        data = {
            "type": "home.SimplePage",
            "create_schema": {
                "required": [],
                "properties": {
                    "body": {"type": "string", "title": "Body"},
                },
            },
            "streamfield_blocks": {},
            "richtext_fields": ["body"],
        }
        result = format_schema_detail(data)
        assert "RichText" in result

    def test_regular_string_not_annotated(self):
        data = {
            "type": "blog.BlogPage",
            "create_schema": {
                "required": [],
                "properties": {
                    "slug": {"type": "string", "title": "Slug"},
                },
            },
            "streamfield_blocks": {},
            "richtext_fields": [],
        }
        result = format_schema_detail(data)
        assert "RichText" not in result
        assert "StreamField" not in result
        assert "string" in result
