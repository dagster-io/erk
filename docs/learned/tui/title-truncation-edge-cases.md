---
title: Title Truncation Edge Cases
read_when:
  - "implementing title truncation in TUI"
  - "troubleshooting truncated titles showing only prefix"
  - "working with title display lengths"
---

# Title Truncation Edge Cases

Title truncation interacts unexpectedly with prefixes and markup. This document covers edge cases to watch for.

## The Basic Problem

When truncation is applied after prefixing:

```
Original:  "Short Title"
+ Prefix:  "[erk-learn] Short Title"  (24 chars)
Truncated: "[erk-learn] Short Ti..."  (20 chars visible)
```

The `[erk-learn] ` prefix consumes 12 characters of the display budget.

## Edge Cases

### Prefix Longer Than Truncation Limit

If truncation limit is 15 chars and prefix is 12:

```
"[erk-learn] My..."  # Only 3 chars of actual title visible
```

### Double Truncation

If source data is already truncated, then prefix added:

```
Original from API: "Very Long Title That Was Alr..."  (already 30 chars)
+ Prefix:          "[erk-learn] Very Long Title That Was Alr..."  (42 chars)
Truncated again:   "[erk-learn] Very Long Titl..."  (30 chars)
```

Content is lost in both truncation passes.

### Markup Overhead

If using Rich markup for styling:

```
# Display budget: 30 chars
# Visible chars:  30
"[bold][erk-learn][/bold] Title"  # Actually ~40 chars with markup
```

Markup tags consume string length but not visible width. Truncation based on string length cuts visible content short.

## Recommended Approach

### Order of Operations

```
1. Truncate raw title first (before prefix)
2. Add prefix to truncated title
3. Apply Text() wrapping for DataTable
```

This ensures the prefix is always fully visible.

### Calculate Available Space

```python
MAX_DISPLAY = 50
PREFIX_LEN = len("[erk-learn] ")  # 12

available_for_title = MAX_DISPLAY - PREFIX_LEN  # 38 chars
```

### Use Character Count, Not String Length

For Rich markup strings, use `len(Text.from_markup(s).plain)` to get visible character count rather than `len(s)`.

## Related Topics

- [TUI Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md) - Full data flow
- [DataTable Markup Escaping](../textual/datatable-markup-escaping.md) - Why markup affects display
