# wagapi

A CLI client for [wagtail-write-api](https://github.com/tomdyson/wagtail-write-api), optimised for LLM orchestration.

`wagapi` is a thin, predictable HTTP client that translates CLI commands into wagtail-write-api HTTP calls and returns structured output. The intelligence lives in the LLM that orchestrates it.

```bash
# Discover the content model
wagapi schema

# Learn the fields for a page type
wagapi schema blog.BlogPage

# Create a page with markdown body
wagapi pages create blog.BlogPage \
  --parent /blog/ \
  --title "Iris Murdoch: The Sovereignty of Good" \
  --body "## A Philosopher and Novelist

Iris Murdoch (1919–1999) was an Irish-British novelist and philosopher..." \
  --publish
```

## Installation

```bash
# One-shot via uvx (no install needed)
uvx wagapi pages list

# Or install permanently
pip install wagapi
# or
uv tool install wagapi
```

**Python 3.10+ required.**

## Configuration

### Quick start

```bash
wagapi init
```

This interactively prompts for your API URL and token, tests the connection, and writes `~/.wagapi.toml`.

### Environment variables

```bash
export WAGAPI_URL=https://cms.example.com/api/write/v1
export WAGAPI_TOKEN=abc123def456
```

### Config priority

Settings are resolved in this order (highest priority first):

| Priority | Source | Example |
|---|---|---|
| 1 (highest) | CLI flags | `--url`, `--token` |
| 2 | Environment variables | `WAGAPI_URL`, `WAGAPI_TOKEN` |
| 3 | Project dotfile | `./.wagapi.toml` |
| 4 (lowest) | User dotfile | `~/.wagapi.toml` |

### Dotfile format

```toml
# ~/.wagapi.toml
url = "https://cms.example.com/api/write/v1"
token = "abc123def456"
rich_text_format = "markdown"   # optional
```

## Output behaviour

| Context | Format | Rationale |
|---|---|---|
| stdout is a TTY | Human-readable summary | User is reading |
| stdout is piped/redirected | JSON | Consumer is a program or LLM |

Override with `--json` (always JSON) or `--human` (always human-readable).

**Human-readable:**

```
$ wagapi pages create blog.BlogPage --parent 3 --title "Hello"
✓ Created page 42 "Hello" (draft)
  Type: blog.BlogPage
  Parent: 3
```

**JSON (same command, piped):**

```
$ wagapi pages create blog.BlogPage --parent 3 --title "Hello" | cat
{
  "id": 42,
  "title": "Hello",
  "slug": "hello",
  "meta": {
    "type": "blog.BlogPage",
    "live": false,
    "has_unpublished_changes": true,
    "parent_id": 3
  }
}
```

## Commands

### Global flags

| Flag | Env var | Description |
|---|---|---|
| `--url URL` | `WAGAPI_URL` | API base URL |
| `--token TOKEN` | `WAGAPI_TOKEN` | Auth token |
| `--json` | — | Force JSON output |
| `--human` | — | Force human output |
| `--verbose` / `-v` | — | Print HTTP request/response details to stderr |
| `--dry-run` | — | Print the HTTP request that *would* be sent |

### `wagapi init`

Interactive setup that writes `~/.wagapi.toml`:

```
$ wagapi init
Wagtail Write API URL: https://cms.example.com/api/write/v1
API Token: ****************************
Testing connection... ✓ Connected (3 page types found)
Config written to ~/.wagapi.toml
```

If `--url` and `--token` are both provided, skips interactive prompts.

### `wagapi schema`

List all available page types:

```
$ wagapi schema
blog.BlogPage           — "blog page"
  Fields: title, slug, published_date, body, authors
  Parents: blog.BlogIndexPage
  Children: (none)
```

Show full field schema for a specific type:

```
$ wagapi schema blog.BlogPage
blog.BlogPage — "blog page"

  Required fields:
    type          string          Page type (blog.BlogPage)
    parent        integer         Parent page ID or URL path
    title         string          Page title

  Optional fields:
    slug          string          Auto-generated from title if omitted
    published_date string         Publication date
    body          array           StreamField body content

  Allowed parents: blog.BlogIndexPage
  Allowed children: (none)

  StreamField blocks:
    body: heading, paragraph, image
```

JSON output returns the raw schema from the API verbatim, including `create_schema`, `patch_schema`, `read_schema`, and `streamfield_blocks`.

### `wagapi pages list`

```bash
wagapi pages list [OPTIONS]
```

| Option | Description |
|---|---|
| `--type TYPE` | Filter by page type, e.g. `blog.BlogPage` |
| `--parent ID` | Direct children of page ID |
| `--descendant-of ID` | All descendants of page ID |
| `--status STATUS` | `draft`, `live`, or `live+draft` |
| `--slug SLUG` | Exact slug match |
| `--path PATH` | Exact URL path match, e.g. `/blog/my-post/` |
| `--search QUERY` | Full-text search |
| `--order FIELD` | Sort field, e.g. `title`, `-first_published_at` |
| `--limit N` | Items per page (default: 20) |
| `--offset N` | Pagination offset |

### `wagapi pages get`

```bash
wagapi pages get 42
wagapi pages get 42 --version live
```

### `wagapi pages create`

```bash
wagapi pages create <type> --parent ID_OR_PATH --title TITLE [OPTIONS]
```

| Option | Description |
|---|---|
| `--parent ID_OR_PATH` | **Required.** Parent page ID or URL path (e.g. `/blog/`) |
| `--title TITLE` | **Required.** Page title |
| `--slug SLUG` | URL slug (auto-generated from title if omitted) |
| `--field KEY:VALUE` | Set a field value (repeatable) |
| `--body TEXT` | Body content as markdown. Use `-` for stdin |
| `--publish` | Publish immediately (default: create as draft) |
| `--raw` | Treat field values as raw JSON (no auto-wrapping) |

**Simple fields:**

```bash
wagapi pages create blog.BlogPage \
  --parent 3 \
  --title "Iris Murdoch" \
  --field published_date:2026-04-06
```

**Markdown body (auto-converted to StreamField):**

```bash
wagapi pages create blog.BlogPage \
  --parent /blog/ \
  --title "Iris Murdoch" \
  --body "## Early Life

Iris Murdoch was born in Dublin in 1919.

## Philosophy

She argued that moral progress comes from **attention**."
```

This auto-wraps the markdown into StreamField blocks: `## Heading` becomes a heading block, paragraphs become paragraph blocks with `format: markdown`.

**Raw mode for full StreamField control:**

```bash
wagapi pages create blog.BlogPage \
  --parent 3 \
  --title "Iris Murdoch" \
  --raw \
  --field 'body:[{"type":"paragraph","value":"<p>Hello</p>","id":"abc123"}]'
```

**Reading from stdin:**

```bash
cat post.md | wagapi pages create blog.BlogPage \
  --parent /blog/ --title "Iris Murdoch" --body -
```

### `wagapi pages update`

```bash
wagapi pages update 42 --title "New Title" --publish
```

Same field options as `create` (minus `--parent` and type). Only specified fields are sent (PATCH semantics).

### `wagapi pages delete`

```bash
wagapi pages delete 42
wagapi pages delete 42 --yes   # skip confirmation
```

No confirmation prompt when piped (non-TTY).

### `wagapi pages publish` / `unpublish`

```bash
wagapi pages publish 42
wagapi pages unpublish 42
```

### `wagapi images list`

```bash
wagapi images list [--search QUERY] [--limit N] [--offset N]
```

### `wagapi images get`

```bash
wagapi images get 7
```

## Markdown-to-StreamField conversion

When `--raw` is **not** set and a field is a StreamField, the CLI auto-converts markdown into blocks:

| Markdown | StreamField block |
|---|---|
| `# Heading` | `{"type": "heading", "value": {"text": "...", "size": "h1"}}` |
| `## Heading` | heading with `"size": "h2"` |
| `### Heading` | heading with `"size": "h3"` |
| Paragraph text | `{"type": "paragraph", "value": {"format": "markdown", "content": "..."}}` |
| `![alt](wagapi:image/42)` | `{"type": "image", "value": 42}` |

Each block gets a generated UUID v4 `id`.

The auto-wrapper only produces `heading`, `paragraph`, and `image` blocks. For other block types (e.g. `quote`, `embed`, `code`), use `--raw` mode.

## Error handling

Errors go to stderr. Exit codes:

| Code | Meaning |
|---|---|
| 0 | Success |
| 1 | General / unexpected error |
| 2 | Usage / argument error |
| 3 | Connection / network error |
| 4 | Authentication error (401) |
| 5 | Permission denied (403) |
| 6 | Not found (404) |
| 7 | Validation error (400/422) |

```
$ wagapi pages create blog.BlogPage --parent 2 --title "Oops"
Error: BlogPage cannot be created under HomePage
```

## LLM integration

Include this in your LLM's system prompt to enable wagapi tool use:

```
You have access to `wagapi`, a CLI for managing Wagtail CMS content.

Before creating or updating pages:
1. Run `wagapi schema` to discover available page types
2. Run `wagapi schema <type>` to see the exact fields and StreamField block types

Key commands:
  wagapi schema [type]                   — discover content model and block schemas
  wagapi pages list [--type T] [--slug S] [--path P]  — list/find pages
  wagapi pages get <id>                  — read page detail (latest draft)
  wagapi pages create <type> --parent ID_OR_PATH --title T [--field K:V]... [--body MD] [--publish]
  wagapi pages update <id> [--field K:V]... [--publish]
  wagapi pages delete <id> --yes
  wagapi pages publish <id>
  wagapi images list

The --parent flag accepts a page ID or a URL path (e.g. --parent /blog/).
Body text accepts markdown by default. Use --raw for full StreamField JSON control.
Pages are created as drafts unless --publish is passed.
Output is JSON when piped.
```

### Example LLM tool call sequence

**User:** "Create a blog post about Iris Murdoch and publish it"

```bash
# Step 1: Discover the content model
wagapi schema | cat

# Step 2: Get the BlogPage field schema
wagapi schema blog.BlogPage | cat

# Step 3: Create and publish
wagapi pages create blog.BlogPage \
  --parent /blog/ \
  --title "Iris Murdoch: The Sovereignty of Good" \
  --body "## A Philosopher and Novelist

Iris Murdoch (1919–1999) was an Irish-British novelist and philosopher..." \
  --field published_date:2026-04-06 \
  --publish | cat
```

## Project structure

```
wagapi/
├── __init__.py
├── __main__.py          # python -m wagapi / uvx entry point
├── cli.py               # click group and global options
├── client.py            # httpx-based API client class
├── config.py            # config loading (env → dotfile → defaults)
├── exceptions.py        # error types with exit codes
├── commands/
│   ├── init.py          # wagapi init
│   ├── schema.py        # wagapi schema
│   ├── pages.py         # wagapi pages *
│   └── images.py        # wagapi images *
├── formatting/
│   ├── output.py        # TTY vs JSON output logic
│   └── markdown.py      # markdown → StreamField converter
└── py.typed
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v
```

## Command tree

```
wagapi
├── init                          Configure connection
├── schema                        List all page types
│   └── <type>                    Show field schema for a type
├── pages
│   ├── list                      List pages (with filters)
│   ├── get <id>                  Get page detail
│   ├── create <type>             Create a page
│   ├── update <id>               Update a page
│   ├── delete <id>               Delete a page
│   ├── publish <id>              Publish latest revision
│   └── unpublish <id>            Revert to draft
└── images
    ├── list                      List images
    └── get <id>                  Get image detail
```

## License

MIT
