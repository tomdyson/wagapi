# Plan: Auto-detect StreamFields and convert markdown

## Problem

wagapi hardcodes markdown-to-StreamField conversion to a field literally called
`body` via the `--body` flag. Wagtail pages can have StreamField fields with any
name (`content`, `main_body`, etc.). There's no way to get automatic markdown
conversion for those fields.

## Goal

Any `--field` value targeting a StreamField should automatically get markdown
conversion, regardless of the field's name. No special flags needed — the CLI
should just know.

## How detection works

The existing schema response already contains enough information. The
`streamfield_blocks` dict is keyed by field name — if a field appears there,
it's a StreamField. No API changes needed.

```json
{
  "create_schema": {
    "properties": {
      "body": {"type": "array", "description": "Body"},
      "title": {"type": "string", "description": "Page title"}
    }
  },
  "streamfield_blocks": {
    "body": [{"type": "heading", ...}, {"type": "paragraph", ...}]
  }
}
```

Here, `body` is a StreamField (it's in `streamfield_blocks`), `title` is not.

---

## Changes (all in wagapi)

### 1. Remove `--body` flag

Remove `--body` from both `create` and `update` commands in
`wagapi/commands/pages.py` (lines 146, 200). Remove the body-handling blocks
(lines 168-178, 219-228).

### 2. Add `--streamfield FIELD:MARKDOWN` flag

Add a new `--streamfield` option (repeatable) to both `create` and `update`.
Accepts `FIELD_NAME:MARKDOWN_CONTENT`. Supports `-` as value to read from stdin
(only for a single `--streamfield` usage).

```python
@click.option(
    "--streamfield", "streamfields", multiple=True,
    help="Set StreamField as FIELD:MARKDOWN (repeatable). Use '-' as value for stdin.",
)
```

Processing:
- Parse like `--field` (split on first `:`)
- For each, run `markdown_to_streamfield()` on the value
- Merge into the request data

This flag is the explicit "I know this is a StreamField, convert my markdown"
escape hatch. It works without a schema fetch.

### 3. Auto-detect StreamFields in `--field`

When `--raw` is **not** set and there are `--field` values, fetch the page type
schema and check each field against `streamfield_blocks`.

If a field is a StreamField, run `markdown_to_streamfield()` on its value
instead of sending it as a plain string.

#### Schema fetching

Add a method to `WagtailClient`:

```python
def get_streamfield_names(self, page_type: str) -> set[str]:
    """Return the set of field names that are StreamFields."""
    schema = self.get_page_type_schema(page_type)
    return set(schema.get("streamfield_blocks", {}).keys())
```

#### When to fetch

- **`create`**: page type is already a positional argument — fetch schema once
  before processing fields
- **`update`**: page type is not known — see step 4

**Skip the fetch entirely when:**
- `--raw` is set (no conversion needed)
- There are no `--field` values (nothing to auto-detect)
- Only `--streamfield` values are used (already explicitly marked)

### 4. Add optional `--type` flag to `update`

```python
@click.option("--type", "page_type", default=None,
              help="Page type (enables auto StreamField detection)")
```

If `--type` is provided: fetch schema directly (one request).

If `--type` is not provided but there are `--field` values that need
auto-detection: GET the page first to read `meta.type`, then fetch the schema
(two requests).

If `--raw` is set or there are no `--field` values: no extra requests.

### 5. Update `_parse_fields` to accept StreamField names

Change the signature to accept the set of StreamField names:

```python
def _parse_fields(
    fields: tuple[str, ...],
    raw: bool,
    streamfield_names: set[str] | None = None,
) -> dict:
    result = {}
    for field in fields:
        key, value = field.split(":", 1)
        if raw:
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass
        elif streamfield_names and key in streamfield_names:
            value = markdown_to_streamfield(value)
        result[key] = value
    return result
```

### 6. Update tests

**Remove tests:**
- `test_pages_create_with_body` — replaced by new tests
- `test_pages_create_raw` — rewrite without `--body`

**Add tests:**
- `test_create_field_auto_streamfield` — `--field body:markdown` with schema
  mock returning `streamfield_blocks`, assert StreamField blocks in request
- `test_create_field_non_streamfield` — `--field published_date:2026-01-01`,
  assert plain string in request
- `test_create_streamfield_flag` — `--streamfield content:markdown`, assert
  StreamField blocks without schema fetch
- `test_create_raw_skips_detection` — `--raw --field body:[...]`, assert no
  schema fetch, value sent as JSON
- `test_update_with_type_flag` — `--type blog.BlogPage --field body:markdown`,
  assert one schema fetch (no page GET)
- `test_update_without_type_flag` — `--field body:markdown`, assert page GET
  then schema fetch

### 7. Update README

- Remove all `--body` references
- Document `--streamfield FIELD:MARKDOWN`
- Update examples to use `--field` (which now auto-detects)
- Note that `--streamfield` is available for explicit control or when working
  offline / without schema access
- Update the LLM integration prompt
- Update the command reference table

### 8. Update human-readable schema output

In `format_schema_detail` (`wagapi/formatting/output.py`), annotate fields that
are StreamFields in the field listing:

```
  Required fields:
    title                string          Page title
  Optional fields:
    body                 streamfield     Body (blocks: heading, paragraph, image)
    published_date       string          Published date
```

Cross-reference `streamfield_blocks` to display "streamfield" as the type and
list the available block types.

---

## Breaking changes

- **Removing `--body`** is breaking for existing users and LLM prompts. Since
  this is pre-1.0 and the user base is small, this is acceptable. The README
  and LLM prompt section will be updated to reflect the new interface.
