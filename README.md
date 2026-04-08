# wagapi

A CLI client for [wagtail-write-api](https://github.com/tomdyson/wagtail-write-api), optimised for LLM orchestration.

`wagapi` is a thin, predictable HTTP client that translates CLI commands into wagtail-write-api HTTP calls and returns structured output. The intelligence lives in the LLM that orchestrates it.

```bash
# Discover the content model
wagapi schema

# Learn the fields for a page type
wagapi schema testapp.BlogPage

# Create a page with markdown body
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Iris Murdoch" --field "body:A philosopher and novelist." --publish
```

## Installation

```bash
# One-shot via uvx (no install needed)
uvx wagapi schema

# Or install permanently
pip install wagapi
# or
uv tool install wagapi
```

**Python 3.10+ required.**

## Quick start

### 1. Set up a Wagtail site with wagtail-write-api

Follow the [example app guide](https://tomdyson.github.io/wagtail-write-api/development/example-app/) to get a local Wagtail instance running with [wagtail-write-api](https://github.com/tomdyson/wagtail-write-api):

```bash
cd wagtail-write-api/example
uv run python manage.py migrate
uv run python manage.py seed_demo
uv run python manage.py runserver
```

`seed_demo` prints API tokens for several test users:

```
--- API Tokens ---
  admin: 25e620d83a9c4a591f5986b1b74bbd4b7365c4be
  editor: 4fbeb9c8...
  moderator: 6c8b9634...
  reviewer: a2377491...
```

### 2. Configure wagapi

```bash
export WAGAPI_URL=http://localhost:8000/api/write/v1
export WAGAPI_TOKEN=25e620d83a9c4a591f5986b1b74bbd4b7365c4be
```

Or run `wagapi init` to save credentials to `~/.wagapi.toml`.

### 3. Explore the content model

```bash
wagapi schema
```

```
testapp.SimplePage                  — "simple page"
  Fields: title, slug, alias_of, body, id
  Parents: wagtailcore.Page, testapp.SimplePage, testapp.EventPage
  Children: wagtailcore.Page, testapp.SimplePage, testapp.BlogIndexPage, testapp.EventPage

testapp.BlogPage                    — "blog page"
  Fields: title, slug, alias_of, published_date, feed_image, body, authors, id
  Parents: testapp.BlogIndexPage
  Children: (none)
...
```

Get the full field schema for a type:

```bash
wagapi schema testapp.BlogPage
```

### 4. Browse existing pages

```bash
wagapi pages list
wagapi pages get 3   # use an ID from the list above
```

### 5. Create a page

```bash
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Iris Murdoch" \
  --field "body:## A Philosopher and Novelist

Iris Murdoch (1919–1999) was an Irish-British novelist and philosopher.

She argued that moral progress comes from **attention**."
```

The `--field` flag auto-detects StreamField and RichTextField fields via the schema. StreamField values are converted from markdown to blocks; RichTextField values are sent as markdown for server-side conversion. Values starting with `[` or `{` are auto-parsed as JSON.

### 6. Publish, update, and manage

```bash
# Publish a draft (use the page ID returned by create)
wagapi pages publish <ID>

# Update a page
wagapi pages update <ID> --title "Iris Murdoch: The Sovereignty of Good"

# Create and publish in one step, using a URL path as parent
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Simone Weil" \
  --field "body:Simone Weil was a French philosopher and mystic." \
  --field published_date:2026-04-07 \
  --publish

# Unpublish
wagapi pages unpublish <ID>

# Delete (prompts for confirmation)
wagapi pages delete <ID>
```

### 7. Inspect requests

```bash
# See HTTP request/response details
wagapi -v pages get <ID>

# Preview without executing
wagapi --dry-run pages create testapp.SimplePage --parent / --title "Test"
```

### 8. Pipe-friendly JSON output

When piped, output is JSON automatically:

```bash
wagapi pages list | jq '.items[].title'
wagapi schema testapp.BlogPage | cat
```

Force a format with `--json` or `--human`:

```bash
wagapi --human pages list
wagapi --json pages get 42
```

## Configuration

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

List available page types, or show the full field schema for a specific type:

```bash
wagapi schema                      # list page types (default)
wagapi schema --snippets           # list snippet types only
wagapi schema --all                # list both page and snippet types
wagapi schema testapp.BlogPage     # show fields, parents, children
wagapi schema --snippets testapp.Category  # show snippet schema
```

JSON output returns the raw schema from the API verbatim, including `create_schema`, `patch_schema`, and `read_schema`.

### `wagapi pages list`

```bash
wagapi pages list [OPTIONS]
```

| Option | Description |
|---|---|
| `--type TYPE` | Filter by page type, e.g. `testapp.BlogPage` |
| `--parent ID_OR_PATH` | Direct children of page ID or URL path (e.g. `5` or `/blog/`) |
| `--descendant-of ID_OR_PATH` | All descendants of page ID or URL path |
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
| `--field KEY:VALUE` | Set a field value (repeatable). StreamField/RichTextField auto-detected via schema. Values starting with `[` or `{` are auto-parsed as JSON |
| `--publish` | Publish immediately (default: create as draft) |

**Auto-detected field conversion:**

`--field` fetches the page type schema and auto-detects the field type:
- **StreamField**: markdown is converted to blocks
- **RichTextField**: markdown is sent as-is for server-side conversion
- **JSON values**: arrays (`[...]`) and objects (`{...}`) are auto-parsed
- **Other fields**: sent as plain strings

```bash
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Iris Murdoch" \
  --field "body:## Early Life

Iris Murdoch was born in Dublin in 1919.

## Philosophy

She argued that moral progress comes from **attention**."
```

**With extra fields:**

```bash
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Iris Murdoch" --field published_date:2026-04-06
```

**JSON field values (auto-detected):**

```bash
# Arrays and objects are auto-parsed as JSON
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Iris Murdoch" \
  --field 'authors:[{"name": "Jo", "role": "Writer"}]' \
  --field published_date:2026-04-06
```

**Full StreamField JSON control:**

```bash
# Pass pre-built StreamField blocks as a JSON array
wagapi pages create testapp.BlogPage --parent /blog/ \
  --title "Iris Murdoch" \
  --field 'body:[{"type":"paragraph","value":"<p>Hello</p>","id":"abc123"}]'
```

### `wagapi pages update`

```bash
wagapi pages update 42 --title "New Title" --publish
```

Same field options as `create` (minus `--parent`). Only specified fields are sent (PATCH semantics). Use `--type` to enable auto StreamField detection without an extra page GET.

**Block-level StreamField editing:**

Instead of replacing the entire body, you can append or insert individual blocks. The CLI fetches the current body, splices in the new block(s), and sends the result.

```bash
# Append a block to the end of the body
wagapi pages update 42 --append-block '{"type":"image","value":7}'

# Insert at a specific position (0-indexed)
wagapi pages update 42 --insert-block 1 '{"type":"paragraph","value":"<p>New paragraph</p>"}'

# Multiple operations in one call
wagapi pages update 42 \
  --insert-block 0 '{"type":"heading","value":{"text":"Preface","size":"h1"}}' \
  --append-block '{"type":"paragraph","value":"<p>Epilogue</p>"}'
```

| Option | Description |
|---|---|
| `--append-block JSON` | Append a block to the end of body (repeatable) |
| `--insert-block INDEX JSON` | Insert a block at INDEX in body (repeatable) |

A UUID `id` is auto-generated for each block unless one is provided.

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

### `wagapi images list` / `get`

```bash
wagapi images list [--search QUERY] [--limit N] [--offset N]
wagapi images get 7
```

### `wagapi snippets`

```bash
wagapi snippets list <type> [--search QUERY] [--limit N] [--offset N]
wagapi snippets get <type> <id>
wagapi snippets create <type> --field name:VALUE [--field slug:VALUE] ...
wagapi snippets update <type> <id> --field name:VALUE ...
wagapi snippets delete <type> <id> [--yes]
```

The `<type>` argument is always required (e.g. `testapp.Category`) because each snippet model lives in its own database table.

## Markdown-to-StreamField conversion

When a field is a StreamField (auto-detected via schema), the CLI converts markdown into blocks:

| Markdown | StreamField block |
|---|---|
| `# Heading` | `{"type": "heading", "value": {"text": "...", "size": "h1"}}` |
| `## Heading` | heading with `"size": "h2"` |
| `### Heading` | heading with `"size": "h3"` |
| Paragraph text | `{"type": "paragraph", "value": "<p>...</p>"}` |
| `- item` (bullet list) | `{"type": "paragraph", "value": "<ul><li>...</li></ul>"}` |
| `1. item` (ordered list) | `{"type": "paragraph", "value": "<ol><li>...</li></ol>"}` |
| `![alt](wagapi:image/42)` | `{"type": "image", "value": 42}` |

Each block gets a generated UUID v4 `id`.

The auto-wrapper only produces `heading`, `paragraph`, and `image` blocks. For other block types (e.g. `quote`, `embed`, `code`), pass pre-built JSON: `--field 'body:[{"type":"quote","value":"..."}]'`.

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
  wagapi pages create <type> --parent ID_OR_PATH --title T [--field K:V]... [--publish]
  wagapi pages update <id> [--type T] [--field K:V]... [--append-block JSON]... [--insert-block IDX JSON]... [--publish]
  wagapi pages delete <id> --yes
  wagapi pages publish <id>
  wagapi snippets list <type>             — list snippets of a type
  wagapi snippets get <type> <id>        — get snippet detail
  wagapi snippets create <type> [--field K:V]...  — create a snippet
  wagapi images list

The --parent flag accepts a page ID or a URL path (e.g. --parent /blog/).
--field auto-detects StreamField and RichTextField via schema — just pass markdown.
Values starting with [ or { are auto-parsed as JSON for full StreamField control.
To add a block (e.g. an image) to an existing page without replacing the whole body:
  wagapi pages update <id> --append-block '{"type":"image","value":<image_id>}'
  wagapi pages update <id> --insert-block <position> '{"type":"image","value":<image_id>}'
Pages are created as drafts unless --publish is passed.
Output is JSON when piped.
```

### Example LLM tool call sequence

**User:** "Create a blog post about Iris Murdoch and publish it"

```bash
# Step 1: Discover the content model
wagapi schema | cat

# Step 2: Get the BlogPage field schema
wagapi schema testapp.BlogPage | cat

# Step 3: Create and publish
wagapi pages create testapp.BlogPage \
  --parent /blog/ \
  --title "Iris Murdoch: The Sovereignty of Good" \
  --field "body:## A Philosopher and Novelist

Iris Murdoch (1919–1999) was an Irish-British novelist and philosopher..." \
  --field published_date:2026-04-06 \
  --publish | cat
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
│   ├── update <id>               Update a page (supports --append-block, --insert-block)
│   ├── delete <id>               Delete a page
│   ├── publish <id>              Publish latest revision
│   └── unpublish <id>            Revert to draft
├── snippets
│   ├── list <type>               List snippets of a type
│   ├── get <type> <id>           Get snippet detail
│   ├── create <type>             Create a snippet
│   ├── update <type> <id>        Update a snippet
│   └── delete <type> <id>        Delete a snippet
└── images
    ├── list                      List images
    └── get <id>                  Get image detail
```

## License

MIT
