---
title: Roadmap Format Versioning
read_when:
  - working on roadmap parser changes
  - understanding backward compatibility for roadmap tables
  - migrating from 4-column to 7-column format
---

# Roadmap Format Versioning

The roadmap parser supports dual-format backward compatibility to allow gradual migration from the legacy 4-column table format to the extended 7-column format.

## Format Evolution

### Legacy Format (4 columns)

**Table header**:

```markdown
| Step | Description | Status | PR |
```

**Columns**:

1. **Step**: Step ID (e.g., "1.1", "2.3")
2. **Description**: What the step does
3. **Status**: One of: pending, done, in_progress, blocked, skipped
4. **PR**: PR reference ("#123") or plan reference ("plan #456")

**Example**:

```markdown
| Step | Description         | Status      | PR       |
| ---- | ------------------- | ----------- | -------- |
| 1.1  | Add user auth       | done        | #123     |
| 1.2  | Add password reset  | in_progress | plan #45 |
| 1.3  | Add OAuth providers | pending     | -        |
```

### Extended Format (7 columns, planned)

**Table header**:

```markdown
| Step | Description | Status | PR | Type | Issue | Depends On |
```

**Additional columns**: 5. **Type**: Step type — "task" (default), "milestone", "research" 6. **Issue**: GitHub issue reference (e.g., "#456") for tracking work 7. **Depends On**: Comma-separated list of step IDs this step depends on (e.g., "1.1,2.3")

**Example**:

```markdown
| Step | Description         | Status      | PR       | Type      | Issue | Depends On |
| ---- | ------------------- | ----------- | -------- | --------- | ----- | ---------- |
| 1.1  | Add user auth       | done        | #123     | task      | #120  | -          |
| 1.2  | Add password reset  | in_progress | plan #45 | task      | #125  | 1.1        |
| 1.3  | Add OAuth providers | pending     | -        | milestone | #130  | 1.1,1.2    |
```

## Dual-Format Parser Strategy

**Parser behavior**: "Try new, fall back to old"

```python
def parse_roadmap_table(phase_body: str) -> list[RoadmapStep]:
    """Parse roadmap table with backward compatibility.

    Tries 7-column format first, falls back to 4-column if header doesn't match.
    """
    # Check for 7-column header
    seven_col_header = re.search(
        r'| Step | Description | Status | PR | Type | Issue | Depends On |',
        phase_body
    )

    if seven_col_header:
        return parse_seven_column_table(phase_body)
    else:
        # Fall back to legacy 4-column parser
        return parse_four_column_table(phase_body)
```

**Key insight**: The header line determines which parser to use. No version field or metadata needed.

## Default Value Assignment

When parsing 4-column tables, missing fields get default values for compatibility with 7-column data structures:

| Field      | Default Value | Rationale                             |
| ---------- | ------------- | ------------------------------------- |
| step_type  | "task"        | Most steps are tasks                  |
| issue      | `None`        | Legacy roadmaps didn't track issues   |
| depends_on | `None`        | No dependency info in 4-column format |

**Example transformation**:

**4-column input**:

```markdown
| 1.1 | Add auth | done | #123 |
```

**Parsed RoadmapStep**:

```python
RoadmapStep(
    id="1.1",
    description="Add auth",
    status="done",
    pr="#123",
    step_type="task",        # DEFAULT
    issue=None,              # DEFAULT
    depends_on=None          # DEFAULT
)
```

## Migration Path

### For Existing Objectives

**No action required**. The parser will continue to read 4-column tables correctly.

### For New Objectives

**Opt-in to 7-column format** by using the extended header:

```markdown
| Step | Description | Status | PR | Type | Issue | Depends On |
```

### Gradual Migration

Objectives can be migrated one at a time:

1. Update table header to 7-column format
2. Fill in Type column (use "task" for most steps)
3. Add Issue references if tracking work separately
4. Add Depends On references for dependency tracking

The parser handles both formats in the same objective body — different phases can use different formats.

## Serialization

When serializing roadmap data back to markdown:

- **If all steps use defaults** (step_type="task", issue=None, depends_on=None): Output 4-column format
- **If any step has non-default values**: Output 7-column format for entire phase

This minimizes migration disruption — old roadmaps stay in old format unless explicitly extended.

## Related Documentation

- [roadmap-parser-api.md](roadmap-parser-api.md) - RoadmapStep dataclass definition
- [roadmap-validation.md](roadmap-validation.md) - Validation checks 6-7 for 7-column format
