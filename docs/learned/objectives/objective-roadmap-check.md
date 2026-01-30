---
title: objective-roadmap-check Command
read_when:
  - "working with objective roadmap markdown tables"
  - "parsing or validating objective structure"
  - "implementing objective progress tracking"
  - "debugging roadmap parsing issues"
tripwires:
  - action: "manually parsing objective roadmap markdown"
    warning: "Use `erk exec objective-roadmap-check` command. It handles regex patterns for phase headers, table columns, status inference, and validation."
---

# objective-roadmap-check Command

Exec script that parses and validates objective roadmap markdown tables, extracting structured phase and step information with status inference.

## Purpose

Parse objective issue bodies containing phase-based roadmap tables and return validated structured JSON for downstream tools (progress tracking, PR linking, next-step inference).

## Usage

```bash
erk exec objective-roadmap-check <OBJECTIVE_NUMBER>
```

**Example:**

```bash
erk exec objective-roadmap-check 6234
```

## JSON Output Schema

```json
{
  "valid": true,
  "issue_number": 6234,
  "title": "Implement User Authentication System",
  "phases": [
    {
      "phase_number": 1,
      "phase_name": "Database Setup",
      "steps": [
        {
          "step_id": "1.1",
          "description": "Create user table schema",
          "status": "done",
          "pr": "#123"
        },
        {
          "step_id": "1.2",
          "description": "Add migration scripts",
          "status": "in_progress",
          "pr": "plan #456"
        }
      ]
    }
  ],
  "summary": {
    "total_phases": 3,
    "total_steps": 12,
    "completed_steps": 4,
    "in_progress_steps": 2,
    "pending_steps": 5,
    "blocked_steps": 1
  },
  "next_step": {
    "phase_number": 1,
    "step_id": "1.3",
    "description": "Test migration rollback"
  },
  "validation_errors": []
}
```

## Markdown Table Format

### Phase Header

Phase headers must match this pattern:

```markdown
### Phase N: Title
```

- **N** must be a digit (sequential numbering expected)
- **Title** is freeform text
- Optional trailing `(N PR)` count is ignored

**Examples:**

```markdown
### Phase 1: Setup
### Phase 2: Implementation
### Phase 3: Testing (3 PR)
```

### Table Structure

Each phase must contain a markdown table with this exact header:

```markdown
| Step | Description | Status | PR |
|------|-------------|--------|-----|
```

**Column Requirements:**

- **Step**: Step ID in format `N.M` (e.g., `1.1`, `2.3`)
- **Description**: Freeform step description
- **Status**: Optional status keyword (see Status Inference below)
- **PR**: PR reference (`#123`, `plan #456`, or `-`)

**Example Table:**

```markdown
| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Create schema | | #123 |
| 1.2 | Add migrations | | plan #456 |
| 1.3 | Test rollback | pending | - |
```

## Status Inference Hierarchy

The command infers step status using a 3-tier hierarchy (highest priority first):

### Tier 1: Explicit Status Column

If the Status column contains these keywords, use them directly:

- `blocked` → status = `"blocked"`
- `skipped` → status = `"skipped"`

**Note**: These override PR column inference.

### Tier 2: PR Column Presence

If Status column is empty or not a keyword, check PR column:

| PR Column Value | Inferred Status  | Meaning                      |
| --------------- | ---------------- | ---------------------------- |
| `#123`          | `"done"`         | PR merged                    |
| `plan #456`     | `"in_progress"`  | Plan exists but not merged   |
| `-` or empty    | `"pending"`      | Not started                  |

### Tier 3: Default

If neither Status nor PR columns provide information:

- Default status = `"pending"`

### Status Value Reference

| Status        | Meaning                     | How Inferred                        |
| ------------- | --------------------------- | ----------------------------------- |
| `done`        | Step completed              | PR column has `#N`                  |
| `in_progress` | Step being worked on        | PR column has `plan #N`             |
| `pending`     | Not started                 | Default (no status, no PR)          |
| `blocked`     | Blocked by dependency       | Explicit Status = `blocked`         |
| `skipped`     | Intentionally skipped       | Explicit Status = `skipped`         |

## Validation Rules

The command validates:

### 1. Phase Headers

- At least one phase header must exist
- Pattern: `### Phase N: Title`
- Phase numbers should be sequential (warning if not)

### 2. Table Headers

Each phase must have a table with header:

```
| Step | Description | Status | PR |
```

Case-insensitive matching. Missing table → validation error.

### 3. Table Separator

Table must have separator line after header:

```
|------|-------------|--------|-----|
```

Missing separator → validation error.

### 4. Step ID Format

- Expected format: `N.M` where N is phase number
- Warning (not error) if format is `NA.M` (letter suffixes)
- Suggestion: prefer plain numbers (`1.1` not `1A.1`)

### 5. Table Rows

- Phase must have at least one table row
- Empty phase → validation error

## Exit Codes

| Code | Meaning                                | JSON Output     |
| ---- | -------------------------------------- | --------------- |
| 0    | Success (roadmap parsed, may have warnings) | `valid: true`   |
| 1    | Critical failure (issue not found, no phases, invalid structure) | `valid: false`  |

**Important**: Validation warnings (like letter-format step IDs) don't cause exit code 1. The command still returns success with warnings in `validation_errors` array.

## Test Coverage

The command has comprehensive test coverage (803 lines in test file):

- 21 test cases covering:
  - Valid roadmap parsing
  - Status inference (all 5 statuses)
  - PR column parsing (`#123`, `plan #456`, `-`)
  - Missing table headers
  - Missing separator lines
  - Empty phases
  - Multiple phases
  - Letter-format step IDs (warning case)
  - Edge cases (empty PR column, whitespace handling)

See `tests/unit/cli/commands/exec/scripts/test_objective_roadmap_check.py` for complete coverage.

## Regex Patterns Reference

### Phase Header Pattern

```python
r"^###\s+Phase\s+(\d+)([A-Z]?):\s*(.+?)(?:\s+\(\d+\s+PR\))?$"
```

**Captures:**

1. Phase number (digits)
2. Optional letter suffix (captured but warned)
3. Phase title (trimmed)
4. Optional trailing `(N PR)` count (ignored)

### Table Header Pattern

```python
r"^\|\s*Step\s*\|\s*Description\s*\|\s*Status\s*\|\s*PR\s*\|$"
```

Case-insensitive, allows whitespace around column names.

### Table Separator Pattern

```python
r"^\|[\s:-]+\|[\s:-]+\|[\s:-]+\|[\s:-]+\|$"
```

Matches separator lines with hyphens/colons/spaces.

### Table Row Pattern

```python
r"^\|(.+?)\|(.+?)\|(.+?)\|(.+?)\|$"
```

**Captures:** 4 columns (Step, Description, Status, PR).

## Related Documentation

- [erk exec Commands](../cli/erk-exec-commands.md) - Command reference
- [Objective Lifecycle](objective-lifecycle.md) - Objective workflow (if exists)
- [Glossary](../glossary.md) - Objective terminology
