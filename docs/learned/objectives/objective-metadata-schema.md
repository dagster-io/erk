---
title: Objective Metadata Schema
read_when:
  - working with objective issue frontmatter
  - implementing parent_objective field
  - understanding objective vs plan metadata
tripwires:
  - action: "adding metadata fields to objective issues without schema definition"
    warning: "Objective metadata must be defined in ObjectiveHeaderSchema (parallel to PlanHeaderSchema). Define schema first, then implement parsing."
---

# Objective Metadata Schema

Objective issues use YAML frontmatter to store structured metadata, similar to how plan issues use PlanHeaderSchema. This document defines the ObjectiveHeaderSchema structure and field semantics.

## ObjectiveHeaderSchema (Planned)

**Status**: Not yet implemented. This documents the planned schema for when it's added.

**Location**: `packages/erk-shared/src/erk_shared/metadata/objective_header.py` (planned)

**Structure**:

```python
@dataclass(frozen=True)
class ObjectiveHeaderSchema:
    """YAML frontmatter schema for erk-objective issues.

    Parallel to PlanHeaderSchema but for objective issues.
    """

    objective_id: str
    """Unique identifier for this objective (same as issue number)."""

    title: str
    """Objective title (synced from issue title)."""

    created_at: str
    """ISO 8601 timestamp when objective was created."""

    parent_objective: str | None
    """Issue reference to parent objective (e.g., "#123") or None for top-level objectives."""

    status: str
    """Overall objective status: "active", "completed", "blocked", "archived"."""

    total_steps: int
    """Total number of steps across all phases in the roadmap."""

    completed_steps: int
    """Number of steps with status "done"."""
```

## Field Definitions

### objective_id

**Type**: `str`

**Format**: Issue number as string (e.g., `"123"`)

**Purpose**: Unique identifier for the objective, matching the GitHub issue number.

**Example**: `"6652"`

### title

**Type**: `str`

**Format**: Plain text matching the GitHub issue title

**Purpose**: Human-readable objective name

**Sync**: Updated when issue title changes

**Example**: `"Add parent_objective Field to Objective Issue Metadata"`

### created_at

**Type**: `str`

**Format**: ISO 8601 timestamp

**Purpose**: Track when objective was created

**Example**: `"2026-01-15T14:23:00Z"`

### parent_objective

**Type**: `str | None`

**Format**: GitHub issue reference (e.g., `"#123"`) or `None`

**Purpose**: Link objectives in hierarchies

**Semantics**:

- `None` = Top-level objective (no parent)
- `"#123"` = This objective is a sub-objective of #123

**Example**:

```yaml
parent_objective: "#6640" # This is a sub-objective of #6640
```

**Use case**: Breaking large objectives into smaller, manageable pieces while maintaining traceability.

### status

**Type**: `str`

**Values**: `"active"`, `"completed"`, `"blocked"`, `"archived"`

**Purpose**: Overall objective state (independent of individual step statuses)

**Inference**:

- `"active"` = Objective is being worked on
- `"completed"` = All steps done, objective achieved
- `"blocked"` = Cannot proceed due to external blocker
- `"archived"` = No longer relevant, abandoned

**Example**: `"active"`

### total_steps / completed_steps

**Type**: `int`

**Purpose**: Progress tracking at objective level

**Computation**: Derived from roadmap table parsing

**Example**:

```yaml
total_steps: 24
completed_steps: 12
```

**Progress calculation**: `completed_steps / total_steps * 100 = 50%`

## Backward Compatibility

**Key design constraint**: Objectives without frontmatter must remain valid.

**Pattern**: If an objective issue has no frontmatter, it's treated as plain markdown:

- No structured metadata
- Roadmap parsing works as before
- No parent_objective tracking

**Migration**: Existing objectives don't break when ObjectiveHeaderSchema is added. They continue to work without frontmatter until explicitly migrated.

## Comparison to PlanHeaderSchema

| Field               | ObjectiveHeaderSchema | PlanHeaderSchema       |
| ------------------- | --------------------- | ---------------------- |
| ID field            | `objective_id`        | `plan_id`              |
| Title               | `title`               | `title`                |
| Created timestamp   | `created_at`          | `created_from_session` |
| Parent relationship | `parent_objective`    | (none)                 |
| Status              | `status`              | (derived from roadmap) |
| Progress tracking   | `total_steps`         | (derived from roadmap) |

**Key difference**: Objectives support hierarchies via `parent_objective`. Plans are flat.

## YAML Frontmatter Example

```yaml
---
objective_id: "6652"
title: "Add parent_objective Field to Objective Issue Metadata"
created_at: "2026-01-15T14:23:00Z"
parent_objective: "#6640"
status: "active"
total_steps: 9
completed_steps: 0
---
# Add parent_objective Field to Objective Issue Metadata

[Objective body starts here...]
```

## Implementation Checklist

When implementing ObjectiveHeaderSchema:

1. **Define schema** in `erk_shared/metadata/objective_header.py` (parallel to `plan_header.py`)
2. **Add parser** to extract frontmatter from objective issue bodies
3. **Update erk objective commands** to read/write frontmatter
4. **Handle backward compatibility** (objectives without frontmatter)
5. **Add validation** for parent_objective references (ensure target exists and has erk-objective label)
6. **Update documentation** to reflect actual implementation

## Related Documentation

- `packages/erk-shared/src/erk_shared/metadata/plan_header.py` - Template for objective schema structure
- [roadmap-parser-api.md](roadmap-parser-api.md) - Roadmap parsing for total_steps calculation
- `docs/learned/planning/plan-header-schema.md` - Plan metadata schema reference
