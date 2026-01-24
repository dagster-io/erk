# Plan: Create Documentation from Learn Analysis

**Source**: Learn analysis of issue #5779 (TUI not displaying [erk-learn] prefix)
**Session**: 5afb116e-138d-4663-8385-93a2b3979595

## Overview

Create 5 new documentation files, update 1 existing file, and add 4 tripwires based on insights extracted from the intensive planning session for issue #5779.

## Files to Modify

### HIGH Priority - New Documents

#### 1. `docs/learned/textual/datatable-markup-escaping.md` (NEW)

**Purpose**: Document that Textual's DataTable interprets plain strings as Rich markup by default.

**Content**:
```markdown
---
title: DataTable Rich Markup Escaping
read_when:
  - "adding cell values to Textual DataTable"
  - "displaying user-generated text in DataTable"
  - "seeing brackets disappear from table cells"
---

# DataTable Rich Markup Escaping

Textual's DataTable interprets plain strings as Rich markup by default. This causes strings containing brackets like `[erk-learn]` to be treated as non-existent style tags and rendered invisibly.

## Problem

```python
# WRONG - [erk-learn] disappears
table.add_row(plan_number, row.title)  # title = "[erk-learn] My Plan"
```

The `[erk-learn]` prefix is interpreted as a Rich markup tag. Since no such style exists, it renders as empty.

## Solution

Wrap cell values in `Text()` objects to disable markup interpretation:

```python
from rich.text import Text

# CORRECT - [erk-learn] displays properly
values: list[str | Text] = [plan_cell, Text(row.title)]
table.add_row(*values, key=row_key)
```

## Key Distinction

This is different from Rich CLI output escaping:
- **CLI output**: Use `escape_markup()` to escape brackets
- **DataTable cells**: Use `Text()` wrapper to disable interpretation entirely

## Related

- [Textual Quirks - Rich Markup Quirks](quirks.md#rich-markup-quirks) - Covers Label widgets
- [TUI Architecture](../tui/architecture.md) - Data flow through TUI
```

#### 2. `docs/learned/tui/plan-title-rendering-pipeline.md` (NEW)

**Purpose**: Document the 5-step pipeline where TUI title issues can occur.

**Content**:
```markdown
---
title: Plan Title Rendering Pipeline
read_when:
  - "debugging missing prefixes in TUI plan titles"
  - "understanding data flow from GitHub to TUI display"
  - "adding metadata to plan titles in TUI"
---

# Plan Title Rendering Pipeline

TUI plan titles flow through a 5-step pipeline. Issues can occur at any stage.

## Pipeline Stages

1. **GitHub API Response** → Raw issue titles returned from GitHub
2. **Metadata Enrichment** → `[erk-learn]` prefix added for learn plans
3. **Filtering Stage** → Plans filtered by state, labels, etc.
4. **Service Layer** → `IssueInfo` → `Plan` → `PlanRowData` transformation
5. **TUI DataTable** → Renders with or without proper `Text()` wrapping

## Critical Ordering

**ENRICH → FILTER → DISPLAY**

Metadata enrichment (adding prefixes, learn_status) must happen BEFORE filtering. If filtering happens first, the filtered-out items never receive enrichment.

## Data Shape at Each Stage

| Stage | Type | Key Fields |
|-------|------|------------|
| GitHub API | IssueInfo | title, number, labels, state |
| After Enrichment | Plan | title (with prefix), learn_status, learn_plan_issue |
| After Filtering | list[Plan] | Subset with all fields preserved |
| Service Transform | PlanRowData | title (for display), issue_number, pr_display |
| DataTable Cell | str or Text | Raw string or escaped Text object |

## Common Failure Points

1. **Markup Interpretation**: Prefix like `[erk-learn]` treated as Rich tag
2. **Lost in Filtering**: Enrichment happens after filter, missing items
3. **Transformation Drop**: Field not copied during `Plan` → `PlanRowData`

## Related

- [DataTable Markup Escaping](../textual/datatable-markup-escaping.md)
- [TUI Architecture](architecture.md)
```

### MEDIUM Priority - New Documents

#### 3. `docs/learned/planning/learn-plan-metadata-fields.md` (NEW)

**Purpose**: Document learn plan metadata preservation requirements.

**Content**:
```markdown
---
title: Learn Plan Metadata Fields
read_when:
  - "working with learn_status or learn_plan_issue fields"
  - "transforming Plan objects through pipelines"
  - "debugging null learn metadata"
---

# Learn Plan Metadata Fields

Learn plans have special metadata fields that must survive all pipeline transformations.

## Critical Fields

| Field | Type | Purpose |
|-------|------|---------|
| `learn_status` | str \| None | Current learn status: pending, in_progress, completed |
| `learn_plan_issue` | int \| None | Issue number of the associated learn plan |

## Preservation Requirements

These fields must be preserved through:
- GitHub API response parsing
- Metadata enrichment stage
- Filtering operations
- `Plan` → `PlanRowData` transformation
- Any intermediate caching

## Common Failure Modes

1. **Filtered out before enrichment**: If filtering happens before metadata enrichment, learn fields are never set
2. **Lost in transformation**: Field not copied when converting between types
3. **Hand-constructed objects**: Creating `Plan` objects manually without copying all fields

## Best Practices

- Use gateway abstractions that preserve all fields
- Never hand-construct `Plan` objects in business logic
- Test that fields survive round-trip through pipeline
```

#### 4. `docs/learned/tui/title-truncation-edge-cases.md` (NEW)

**Purpose**: Document truncation behavior with metadata prefixes.

**Content**:
```markdown
---
title: Title Truncation Edge Cases
read_when:
  - "implementing title truncation in TUI"
  - "debugging truncated titles losing prefixes"
  - "working with title display length limits"
---

# Title Truncation Edge Cases

Title truncation (47 chars + "...") doesn't account for markup overhead.

## The Problem

When `[erk-learn] ` (12 chars) is added before truncation:
- Original title: 50 chars
- With prefix: 62 chars
- After truncation: 50 chars (47 + "...")
- Visible content: Only 35 chars of original title

If the prefix is interpreted as markup and hidden, the user sees fewer characters than expected with no indication why.

## Considerations

1. **Should truncation happen before or after prefix addition?**
   - Before: Prefix always visible, less original title
   - After: More original title, but prefix may be cut

2. **Should length calculation account for non-visible markup?**
   - Rich markup tags don't contribute to visual width
   - But `[erk-learn]` is meant to be visible, not markup

## Current Behavior

Truncation happens at service layer before TUI rendering. The `[erk-learn]` prefix is counted toward the character limit.

## Related

- [Plan Title Rendering Pipeline](plan-title-rendering-pipeline.md)
```

### MEDIUM Priority - Update Existing

#### 5. `docs/learned/tui/architecture.md` (UPDATE)

**Add section** after "Design Principles" section (~line 176):

```markdown
## Data Shape at Each Layer

When debugging TUI data issues, trace the shape of data at each layer:

| Layer | Type | Key Fields | Notes |
|-------|------|------------|-------|
| GitHub API | `IssueInfo` | title, number, state, labels | Raw API response |
| Enrichment | `Plan` | title, learn_status, learn_plan_issue | Metadata added |
| Filtering | `list[Plan]` | All Plan fields | Subset selection |
| Service | `PlanRowData` | title, pr_display, issue_number | Display-ready |
| Widget | `str \| Text` | Cell values | Must wrap in `Text()` for brackets |

**Example trace for `[erk-learn]` prefix:**
1. GitHub returns: `"Fix the bug"`
2. Enrichment adds: `"[erk-learn] Fix the bug"`
3. Filtering preserves: `"[erk-learn] Fix the bug"`
4. Service passes: `title = "[erk-learn] Fix the bug"`
5. Widget receives: `Text("[erk-learn] Fix the bug")` ← Must wrap!
```

### LOW Priority - New Document

#### 6. `docs/learned/architecture/pipeline-transformation-patterns.md` (NEW)

**Purpose**: Document general principle about enrichment/filter ordering.

**Content**:
```markdown
---
title: Pipeline Transformation Patterns
read_when:
  - "designing multi-stage data pipelines"
  - "deciding order of enrichment vs filtering"
  - "debugging state loss in data transformations"
---

# Pipeline Transformation Patterns

## Ordering Principle

**ENRICH → FILTER → DISPLAY**

Metadata enrichment must happen before filtering. Filtering stages only operate on the subset they return; items filtered out never receive enrichment that happens afterward.

## Diagram

```
[Raw Data] → [Enrich All] → [Filter Subset] → [Transform for Display] → [Render]
     ↓              ↓               ↓                    ↓                  ↓
  Full set     Full set +      Subset with         Display-ready       Final UI
               metadata         metadata            subset
```

## Anti-Pattern

```
[Raw Data] → [Filter Subset] → [Enrich Subset] → [Display]
                    ↓
            Lost items never
            get enriched!
```

## Prevention

- Define enrichment as a pre-filter stage
- Document expected data shape at each stage
- Test that enriched fields survive through to final output
```

### Tripwires to Add

Add 4 tripwires to `docs/learned/tripwires.md`:

```markdown
**CRITICAL: Before adding cell values to Textual DataTable with .add_row()** → Read [DataTable Rich Markup Escaping](textual/datatable-markup-escaping.md) first. Always wrap in `Text(value)` if strings contain user data with brackets. Otherwise `[anything]` will be interpreted as Rich markup.

**CRITICAL: Before using title-stripping functions like _strip_plan_prefixes** → Read [Code Conventions](conventions.md) first. Distinguish `_strip_plan_prefixes` (PR creation) vs `_strip_plan_markers` (plan creation) vs `strip_plan_from_filename` (filename handling). Document distinction to prevent calling wrong function.

**CRITICAL: Before reading learn_plan_issue or learn_status from Plan objects** → Read [Learn Plan Metadata Fields](planning/learn-plan-metadata-fields.md) first. Verify field came through full pipeline. If null, check if filtered out earlier. Use gateway abstractions; never hand-construct Plan objects.

**CRITICAL: Before modifying how plan titles are displayed in TUI** → Read [Plan Title Rendering Pipeline](tui/plan-title-rendering-pipeline.md) first. Ensure `[erk-learn]` prefix is added BEFORE any filtering/sorting stages. Filters applied after prefix addition preserve metadata; filters before lose it.
```

## Implementation Order

1. Create HIGH priority docs first (they're referenced by tripwires)
2. Add tripwires to `tripwires.md`
3. Create MEDIUM priority docs
4. Update `tui/architecture.md` with new section
5. Create LOW priority doc

## Verification

After creating all docs:
1. Run `erk docs sync` to regenerate tripwires
2. Verify tripwire links resolve correctly
3. Check that `docs/learned/index.md` includes new docs (may need regeneration)
4. Run `make format` to ensure markdown formatting is correct