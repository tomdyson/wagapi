from __future__ import annotations

import pytest
from click.testing import CliRunner


@pytest.fixture
def cli_runner():
    return CliRunner()


SAMPLE_PAGE_TYPES = [
    {
        "name": "blog.BlogPage",
        "verbose_name": "blog page",
        "fields": ["title", "slug", "published_date", "body", "authors"],
        "allowed_parents": ["blog.BlogIndexPage"],
        "allowed_children": [],
    },
    {
        "name": "blog.BlogIndexPage",
        "verbose_name": "blog index page",
        "fields": ["title", "slug", "intro"],
        "allowed_parents": ["wagtailcore.Page", "home.HomePage"],
        "allowed_children": ["blog.BlogPage"],
    },
]

SAMPLE_PAGE_TYPE_SCHEMA = {
    "name": "blog.BlogPage",
    "verbose_name": "blog page",
    "create_schema": {
        "required": ["type", "parent", "title"],
        "properties": {
            "type": {"type": "string", "description": "Page type (blog.BlogPage)"},
            "parent": {"type": "integer", "description": "Parent page ID or URL path"},
            "title": {"type": "string", "description": "Page title"},
            "slug": {"type": "string", "description": "Auto-generated from title if omitted"},
            "published_date": {"type": "string", "description": "Publication date"},
            "body": {"type": "array", "description": "StreamField body content"},
        },
    },
    "allowed_parents": ["blog.BlogIndexPage"],
    "allowed_children": [],
    "streamfield_blocks": {
        "body": [
            {"type": "heading"},
            {"type": "paragraph"},
            {"type": "image"},
        ]
    },
}

SAMPLE_PAGE = {
    "id": 42,
    "title": "Hello",
    "slug": "hello",
    "meta": {
        "type": "blog.BlogPage",
        "live": False,
        "has_unpublished_changes": True,
        "parent_id": 3,
    },
}

SAMPLE_PAGE_LIST = {
    "meta": {"total_count": 1},
    "items": [SAMPLE_PAGE],
}

SAMPLE_IMAGE = {
    "id": 7,
    "title": "Hero image",
    "width": 1200,
    "height": 800,
    "meta": {"download_url": "https://cms.example.com/media/images/hero.jpg"},
}

SAMPLE_IMAGE_LIST = {
    "meta": {"total_count": 1},
    "items": [SAMPLE_IMAGE],
}
