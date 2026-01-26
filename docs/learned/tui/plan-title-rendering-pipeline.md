---
title: TUI Plan Title Rendering Pipeline
read_when:
  - "debugging why plan titles display incorrectly"
  - "troubleshooting missing prefixes in TUI"
  - "understanding plan data flow in TUI"
tripwires:
  - action: "modifying how plan titles are displayed in TUI"
    warning: "Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages."
  - action: "using title-stripping functions"
    warning: "Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling)."
---

# TUI Plan Title Rendering Pipeline

Plan titles pass through multiple stages before appearing in the TUI. Issues can occur at any stage.

## The 5-Stage Pipeline

```
GitHub API → Middleware (prefix) → Filtering → Service (transform) → Widget (render)
```

### Stage 1: GitHub API Response

GitHub returns raw issue/PR data:

```json
{
  "title": "Add dark mode support",
  "labels": ["erk-plan", "erk-learn"]
}
```

At this stage, titles are plain strings without any erk-specific prefixes.

### Stage 2: Middleware Enrichment (BEFORE FILTERING)

**This is the critical stage for prefix addition.** The data provider or service layer adds prefixes based on labels:

- `[erk-learn]` prefix for plans with `erk-learn` label
- Other metadata enrichment (learn_status, learn_plan_issue)

**Ordering Constraint** (referenced by tripwire):

```
✅ CORRECT: Stage 1 → Stage 2 (enrich) → Stage 3 (filter)
❌ WRONG:   Stage 1 → Stage 3 (filter) → Stage 2 (enrich)
```

If enrichment happens after filtering, filtered-out plans don't get their prefixes, and later re-additions will be missing metadata.

### Stage 3: Filtering Stage

Plans are filtered by:

- Labels (show only `erk-plan`, exclude closed)
- Run state (show only running/queued)
- User-defined filters

**Ordering matters**: ENRICH → FILTER → DISPLAY. If filtering happens before enrichment, metadata may be lost.

### Stage 4: Service Transformation

The `PlanListService` transforms raw `Plan` objects to `PlanRowData`:

- Titles may be truncated (47 chars + "...")
- Display fields are pre-formatted
- Timestamps converted to relative time

See [PlanRowData Field Reference](plan-row-data.md) for the complete data shape.

### Stage 5: Widget Rendering

The `PlanTable` widget displays `PlanRowData`:

- Plain strings are interpreted as Rich markup (see [DataTable Markup Escaping](../textual/datatable-markup-escaping.md))
- `[erk-learn]` in title would be eaten by Rich markup parser
- Fix: Wrap title in `Text()` object

## Debugging Checklist

When titles display incorrectly:

1. **Check Stage 1**: Is the raw title correct from GitHub? Use `gh issue view <num> --json title`

2. **Check Stage 2**: Is the prefix being added? Add logging at the enrichment point to verify.

3. **Check Stage 3**: Is filtering removing enriched plans? Verify filter order.

4. **Check Stage 4**: Is truncation too aggressive? The `[erk-learn] ` prefix is 12 characters, reducing visible content.

5. **Check Stage 5**: Is Rich markup eating brackets? Verify `Text()` wrapping is applied.

## Common Issues

### Missing `[erk-learn]` Prefix

**Symptom**: Learn plans show up but without their prefix.

**Root causes**:

- Rich markup interpretation (most common) - wrap in `Text()`
- Prefix added after filtering - reorder stages
- Prefix stripped by truncation - check truncation length

### Metadata Fields Are Null

**Symptom**: `learn_status` or `learn_plan_issue` is None even for learn plans.

**Root causes**:

- Gateway abstraction not preserving fields
- Hand-constructed Plan objects missing fields
- Filtering stage losing metadata

### Title Truncation Hides Prefix

**Symptom**: Only "..." visible for short titles.

**Root cause**: Truncation happens after prefix is added, so `[erk-learn] Sh...` might become just the prefix plus ellipsis.

**Fix**: Account for prefix length when calculating truncation, or truncate before prefixing.

## Related Topics

- [DataTable Markup Escaping](../textual/datatable-markup-escaping.md) - The `Text()` fix
- [TUI Architecture](architecture.md) - Overall data flow
- [PlanRowData Field Reference](plan-row-data.md) - Complete field documentation
