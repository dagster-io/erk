# Learn Plan: TUI DataTable Rich Markup Escaping

**Learned from**: #5779 (Fix: TUI Not Displaying [erk-learn] Prefix in Plan Titles)
**Session**: 5afb116e-138d-4663-8385-93a2b3979595

## Summary

This session uncovered that Textual's DataTable interprets plain strings as Rich markup by default. When `[erk-learn]` appeared in plan titles, it was treated as a non-existent Rich style tag and rendered invisibly. The fix is to wrap cell values in `Text()` objects.

## Documentation Items

### HIGH Priority

#### 1. Textual DataTable Rich Markup Interpretation (NEW)

**Location**: `docs/learned/textual/datatable-markup-escaping.md`

**Content**: Document that Textual's DataTable interprets plain strings as Rich markup by default. Demonstrate the fix: wrap cell values in `Text(value)` to escape markup.

**Key insight**: This is different from Rich CLI output escaping. DataTable requires `Text()` wrapping, not `escape_markup()`.

#### 2. TUI Plan Title Rendering Pipeline (NEW)

**Location**: `docs/learned/tui/plan-title-rendering-pipeline.md`

**Content**: Document the 5-step pipeline where TUI title issues can occur:
1. GitHub API returns raw titles
2. Middleware adds `[erk-learn]` prefix
3. Filtering stage may reorder/lose metadata
4. Service layer transforms to PlanRowData
5. TUI DataTable renders with or without proper Text() wrapping

### MEDIUM Priority

#### 3. Learn Plan Metadata Preservation (NEW)

**Location**: `docs/learned/planning/learn-plan-metadata-fields.md`

**Content**: Document which fields (learn_status, learn_plan_issue) are critical for learn plans and must survive all transformations. Specify which pipeline stages preserve vs. lose metadata.

#### 4. Multi-Layer Data Flow Pattern (UPDATE)

**Location**: `docs/learned/tui/architecture.md`

**Content**: Extend existing doc with "Data Shape at Each Layer" section documenting Plan/PlanRowData shape at API response level, service transformation level, and widget consumption level.

#### 5. Title Truncation with Markup Overhead (NEW)

**Location**: `docs/learned/tui/title-truncation-edge-cases.md`

**Content**: Document that title truncation (47 chars + "...") doesn't account for markup overhead. When `[erk-learn] ` (12 chars) is added before truncation, visible content is reduced.

### LOW Priority

#### 6. Filter Stage Ordering Rules (UPDATE)

**Location**: `docs/learned/architecture/pipeline-transformation-patterns.md`

**Content**: Document principle: metadata enrichment must happen before filtering, not after. Include ordering diagram: ENRICH → FILTER → DISPLAY.

## Tripwires to Add

Add to `docs/learned/tripwires.md`:

1. **Before adding cell values to Textual DataTable**: Always wrap in `Text(value)` if strings contain user data with brackets. Otherwise `[anything]` will be interpreted as Rich markup.

2. **Before using title-stripping functions**: Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling).

3. **Before reading learn_plan_issue or learn_status**: Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects.

4. **Before modifying how plan titles are displayed in TUI**: Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages.

## Prevention Insights

| Error Pattern | Root Cause | Prevention |
|---------------|------------|------------|
| Markup interpretation of data strings | Textual/Rich default behavior | Always wrap user data in `Text()` for DataTable |
| Prefix disappears after filtering | Filter applied before enrichment | Order: ENRICH → FILTER → DISPLAY |
| Metadata becomes null during transformation | Lost in pipeline stage | Use gateway abstractions that preserve all fields |

## Failed Approaches (for future reference)

| What Was Tried | Why It Failed | What Worked |
|----------------|---------------|-------------|
| Grep for `[erk-learn]` in TUI code | Prefix comes from GitHub, not added in TUI | Traced data flow backwards to confirm source |
| Check for explicit stripping functions | No such functions in TUI | Realized issue was markup interpretation |
| Adding prefix at TUI rendering stage | Too late; metadata already lost by filtering | Add prefix at gateway response level |