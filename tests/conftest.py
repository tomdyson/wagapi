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
        "available_parents": [
            {"id": 3, "title": "Blog", "type": "blog.BlogIndexPage", "url_path": "/blog/"},
        ],
    },
    {
        "name": "blog.BlogIndexPage",
        "verbose_name": "blog index page",
        "fields": ["title", "slug", "intro"],
        "allowed_parents": ["wagtailcore.Page", "home.HomePage"],
        "allowed_children": ["blog.BlogPage"],
        "available_parents": [
            {"id": 1, "title": "Root", "type": "wagtailcore.Page", "url_path": "/"},
            {"id": 2, "title": "Home", "type": "home.HomePage", "url_path": "/"},
        ],
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

SAMPLE_RICHTEXT_PAGE_TYPE_SCHEMA = {
    "name": "home.SimplePage",
    "verbose_name": "simple page",
    "create_schema": {
        "required": ["type", "parent", "title"],
        "properties": {
            "type": {"type": "string"},
            "parent": {"type": "integer"},
            "title": {"type": "string"},
            "body": {"type": "string", "description": "RichTextField body content"},
        },
    },
    "allowed_parents": ["wagtailcore.Page"],
    "allowed_children": [],
    "streamfield_blocks": {},
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
    "hints": {
        "publish": "wagapi pages publish 42",
        "edit": "wagapi pages update 42 --title '...' --body '...'",
        "view": "wagapi pages get 42",
        "delete": "wagapi pages delete 42",
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
