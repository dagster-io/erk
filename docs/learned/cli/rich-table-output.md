---
title: Rich Table CLI Output Pattern
read_when:
  - "building CLI tables with color or formatting"
  - "adding Rich output to a Click command"
  - "creating sparklines or colored status indicators in CLI"
tripwires:
  - action: "building CLI tables with Rich"
    warning: "Use Console(stderr=True, force_terminal=True) to avoid breaking piped output. Use escape() on user-provided text. See rich-table-output.md for the full pattern."
---

# Rich Table CLI Output Pattern

Pattern for building rich CLI table output with Click + Rich, including colored sparklines, linked issue numbers, and escaped user text.

## Core Pattern

1. **Build a `Table`** with `box=None` and typed columns
2. **Extract helper functions** for computed fields (slugs, enriched data, sparklines)
3. **Use `Console(stderr=True, force_terminal=True)`** to keep structured output on stderr (preserves `click.echo` stdout for piping)
4. **Escape user text** with `rich.markup.escape()` before inserting into markup strings

## Helper Function Extraction

Complex table rows benefit from extracting per-row computation into helper functions:

- `_compute_slug(plan)` — extract display slug from plan metadata
- `_compute_enriched_fields(plan)` — derive roadmap progress, sparkline, deps from plan body
- `_rich_sparkline(sparkline)` — wrap sparkline characters in Rich color markup

Each helper is a pure function operating on a single plan, making them independently testable.

## Colored Sparkline Pattern

<!-- Source: src/erk/cli/commands/objective/list_cmd.py, _SPARKLINE_RICH_STYLES -->
<!-- Source: src/erk/cli/commands/objective/list_cmd.py, _rich_sparkline -->

Map sparkline characters to Rich markup styles using a `dict[str, str]` mapping and a helper function that joins styled characters. See `_SPARKLINE_RICH_STYLES` and `_rich_sparkline()` in `src/erk/cli/commands/objective/list_cmd.py` for the reference implementation.

## Linked Issue Numbers

Use Rich's `[link=URL]` syntax for clickable issue numbers in terminal emulators that support it:

```python
f"[link={url}]#{identifier}[/link]"
```

See `src/erk/cli/commands/objective/list_cmd.py` for the reference implementation.

## Key Techniques

- **`escape(slug)`** — prevent user-provided text from being parsed as Rich markup
- **`Table(box=None)`** — clean output without box-drawing characters
- **`min_width` on columns** — prevent columns from collapsing when data is short
- **`no_wrap=True`** — keep columns on a single line

## Exemplar

`src/erk/cli/commands/objective/list_cmd.py` — 200-line implementation with all patterns above.

Tests: `tests/unit/cli/commands/objective/test_list_cmd_helpers.py`

## Related Topics

- [PR Submit Pipeline](pr-submit-pipeline.md) — another CLI command with structured output
