---
title: Objective Lifecycle
category: objectives
read_when:
  - "creating or modifying objective lifecycle code"
  - "understanding how objectives are created, mutated, and closed"
  - "adding new mutation paths to objective roadmaps"
tripwires:
  - action: "adding a new roadmap mutation site without updating this document"
    warning: "All roadmap mutation sites must be documented in objective-lifecycle.md"
---

# Objective Lifecycle

This document describes the complete lifecycle of objective issues from creation to closure, including all mutation paths and data flows.

## Overview

Objectives are GitHub issues with the `erk-objective` label that track multi-plan work through a roadmap structure. The roadmap exists in two forms:

1. **Source of truth**: YAML frontmatter in `<!-- erk:metadata-block:objective-roadmap -->` blocks
2. **Rendered view**: Markdown table in the issue body (for human readability)

During the migration period, both frontmatter and table coexist (dual-write strategy). Legacy objectives without frontmatter fall back to table parsing.

## Objective States

Objectives have an implicit state machine based on roadmap step completion:

```
Created → Active → Complete → Closed
```

- **Created**: Objective exists with roadmap, no steps done
- **Active**: At least one step in progress or done
- **Complete**: All steps are done or skipped (terminal step statuses)
- **Closed**: Issue is closed (manually or automatically)

## Creation

Objectives are created through:

1. **Manual creation**: User runs `gh issue create` with `erk-objective` label and roadmap markdown
2. **Assisted creation**: User runs `erk objective create` (slash command) which guides through structured input

### Initial Roadmap Format

When created, objectives have:

- Phase headers: `### Phase N: Name` or `### Phase NA: Name`
- Markdown table with columns: Step | Description | Status | PR
- All steps start with status `pending` and no PR

**Example:**

```markdown
# Objective: Build Authentication System

## Roadmap

### Phase 1: Foundation

| Step | Description     | Status  | PR  |
| ---- | --------------- | ------- | --- |
| 1.1  | Add user model  | pending | -   |
| 1.2  | Add JWT library | pending | -   |

### Phase 2: Implementation

| Step | Description     | Status  | PR  |
| ---- | --------------- | ------- | --- |
| 2.1  | Implement login | pending | -   |
```

**With frontmatter (preferred):**

```markdown
## <!-- erk:metadata-block:objective-roadmap -->

schema_version: "1"
steps:

- id: "1.1"
  description: "Add user model"
  status: "pending"
  pr: null
- id: "1.2"
  description: "Add JWT library"
  status: "pending"
  pr: null
- id: "2.1"
  description: "Implement login"
  status: "pending"
  pr: null

---

<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

[same markdown table as above]
```

## Reading

All roadmap reads go through `parse_roadmap(body: str)` in `objective_roadmap_shared.py`.

### Parsing Flow

```
parse_roadmap(body)
  ↓
  Check for objective-roadmap metadata block
  ↓
  ├─ Metadata block found?
  │  ↓
  │  parse_roadmap_frontmatter()
  │  ↓
  │  ├─ Valid YAML?
  │  │  ↓
  │  │  group_steps_by_phase()
  │  │  ↓
  │  │  enrich_phase_names() (from markdown headers)
  │  │  ↓
  │  │  Return (phases, [])
  │  │
  │  └─ Invalid → Fall through to table parsing
  │
  └─ No metadata block → Table parsing (regex)
      ↓
      Extract phase headers and tables
      ↓
      Parse rows with status inference
      ↓
      Return (phases, validation_errors)
```

### Status Inference (Table Mode Only)

When parsing markdown tables, status is inferred from PR column if status column is `-`:

| PR Column    | Inferred Status |
| ------------ | --------------- |
| `#123`       | `done`          |
| `plan #456`  | `in_progress`   |
| `-` or empty | `pending`       |

Explicit status values (`done`, `in_progress`, `blocked`, `skipped`) override inference.

### Frontmatter Mode

Frontmatter has explicit status, no inference:

- Status comes directly from YAML `status` field
- Phase names extracted from markdown headers (not stored in YAML)
- Phase membership derived from step ID prefix (e.g., "1.2" → phase 1)

## Mutations

All mutations must update **both** frontmatter and table when frontmatter exists (dual-write).

### Mutation Sites

| Site                                    | Type      | Trigger                                       | Updates                     | Frontmatter-Aware?                 |
| --------------------------------------- | --------- | --------------------------------------------- | --------------------------- | ---------------------------------- |
| `update-roadmap-step.py`                | Surgical  | `erk exec update-roadmap-step` or `plan-save` | Single PR cell              | ✅ Yes (this plan)                 |
| `objective-update-with-landed-pr`       | Full-body | After landing PR                              | Roadmap + Current Focus     | ✅ Yes (this plan)                 |
| `plan-save.md` Step 3.5                 | Indirect  | Creating plan from objective                  | Calls `update-roadmap-step` | ✅ Inherits                        |
| `check_cmd.py` / `validate_objective()` | Read-only | `erk objective check`                         | N/A (reads only)            | ✅ Inherits from `parse_roadmap()` |
| `objective_update_context.py`           | Read-only | Fetch context for updates                     | N/A (reads only)            | ✅ Inherits from `parse_roadmap()` |

### Surgical Update: `update-roadmap-step`

**Path**: `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`

**What it does**: Updates a single step's PR reference and recomputes status.

**Mutation flow**:

1. Fetch issue body
2. Check for `objective-roadmap` metadata block
3. **If frontmatter exists:**
   - Parse YAML, find step by ID
   - Update `pr` field, reset `status` to `"pending"` (for re-inference if needed)
   - Serialize back to YAML
   - Replace metadata block
   - **Also** update markdown table (dual-write)
4. **If no frontmatter:**
   - Use regex to find table row by step ID
   - Replace PR and status cells
5. Write updated body to GitHub

**Usage**:

```bash
erk exec update-roadmap-step 6423 --step 1.3 --pr "plan #6464"
erk exec update-roadmap-step 6423 --step 1.3 --pr "#6500"
erk exec update-roadmap-step 6423 --step 1.3 --pr ""  # Clear
```

**Status computation** (table mode):

- `pr` starts with `#` → status = `done`
- `pr` starts with `plan #` → status = `in_progress`
- `pr` is empty → status = `pending`

### Full-Body Update: `objective-update-with-landed-pr`

**Path**: `.claude/commands/erk/objective-update-with-landed-pr.md`

**What it does**: Updates objective after landing a PR. Marks steps as done, posts action comment, updates Current Focus section.

**Mutation flow**:

1. Determine which steps the PR completed (compare plan to roadmap)
2. Compose action comment with summary and lessons learned
3. **Compose updated objective body:**
   - **If frontmatter exists:**
     - Parse YAML frontmatter
     - Update relevant step(s): set `pr: "#<number>"` and `status: "done"`
     - Serialize updated YAML
     - **Also** update markdown table (dual-write)
     - Update "Current Focus" section
   - **If no frontmatter:**
     - Update table: set PR cell to `#<number>`, status to `-`
     - Update "Current Focus" section
4. Post action comment to GitHub
5. Write updated body to GitHub
6. Check if all steps are done/skipped → close objective if complete

**Agent workflow**: Uses subagent pattern. Parent agent discovers context, delegates body composition to subagent.

### Indirect Updates

#### `plan-save.md` Step 3.5

When saving a plan that's part of an objective:

- Calls `erk exec update-roadmap-step <objective> --step <step-id> --pr "plan #<plan-number>"`
- Inherits frontmatter support from `update-roadmap-step`

## Frontmatter Lifecycle

### Migration Path

1. **New objectives**: Created with frontmatter from start (when tooling supports it)
2. **Existing objectives**: Remain table-only until migrated
3. **Migration**: Run `erk exec migrate-objective-roadmap <issue>` to add frontmatter (future)
4. **Dual-write period**: Both frontmatter and table updated during transition
5. **Future**: Table becomes optional rendered view (can be regenerated from frontmatter)

### Frontmatter Schema

```yaml
---
schema_version: "1"
steps:
  - id: "1.1" # Required: step identifier
    description: "..." # Required: human-readable description
    status: "pending" # Required: pending|done|in_progress|blocked|skipped
    pr: null # Optional: null or string like "#123" or "plan #456"
---
```

**Design decisions**:

- **Flat list**: Steps are stored flat, phase membership derived from ID prefix
- **No phase names**: Phase names live only in markdown headers (extracted at read time)
- **Schema versioning**: `schema_version` for future evolution
- **Explicit status**: No inference in frontmatter (unlike tables)

### Coexistence with Tables

During dual-write:

- **Frontmatter** = source of truth for step data
- **Table** = rendered view for human readability
- Mutations update both to keep in sync
- Reads prefer frontmatter, fall back to table
- Tables can drift (frontmatter wins if they conflict)

## Closing

Objectives close when:

1. All roadmap steps are `done` or `skipped`
2. User confirms closure (unless `--auto-close` flag present)
3. `gh issue close <issue-number>` is executed

**Closure triggers**:

- `/erk:objective-update-with-landed-pr` checks completion after each PR lands
- Manual: `erk objective close <issue>` (future command)

**Closure comment format**:

```markdown
## Action: Objective Complete

**Date:** YYYY-MM-DD

All roadmap steps completed:

- N total steps
- N done
- N skipped

[Summary of what was accomplished]
```

## Data Flow Diagram

```
┌─────────────────────────────────────────────────────────┐
│ 1. Creation                                              │
│                                                          │
│ erk objective create → gh issue create                   │
│   ↓                                                      │
│ Issue body with roadmap table (± frontmatter)           │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 2. Plan Linking                                          │
│                                                          │
│ erk plan save (with objective ref)                       │
│   ↓                                                      │
│ update-roadmap-step: set pr="plan #N"                    │
│   ↓                                                      │
│ Roadmap shows plan # in PR column                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 3. PR Landing                                            │
│                                                          │
│ erk land (or gt submit + gh pr merge)                    │
│   ↓                                                      │
│ erk objective-update-with-landed-pr                      │
│   ↓                                                      │
│ - Post action comment                                    │
│ - Update roadmap: pr="#N", status="done"                 │
│ - Update Current Focus                                   │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 4. Step Completion Check                                 │
│                                                          │
│ parse_roadmap() computes summary                         │
│   ↓                                                      │
│ All steps done/skipped?                                  │
│   ├─ Yes → Offer to close objective                      │
│   └─ No → Continue with next step                        │
└─────────────────────────────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│ 5. Closure                                               │
│                                                          │
│ Post completion comment                                  │
│   ↓                                                      │
│ gh issue close <issue>                                   │
│   ↓                                                      │
│ Objective closed                                         │
└─────────────────────────────────────────────────────────┘
```

## Read-Only Consumers

These components read roadmap data but don't mutate:

| Consumer                      | Purpose                         | Frontmatter Support                |
| ----------------------------- | ------------------------------- | ---------------------------------- |
| `check_cmd.py`                | Validate objective structure    | ✅ Inherits from `parse_roadmap()` |
| `objective_update_context.py` | Fetch objective/plan/PR context | ✅ Inherits from `parse_roadmap()` |
| `objective_list.py`           | List all objectives             | ✅ Inherits from `parse_roadmap()` |
| TUI viewers                   | Display objective state         | ✅ Inherits from `parse_roadmap()` |

Read-only consumers automatically gain frontmatter support via `parse_roadmap()`.

## Related Commands

- `erk objective create` - Create new objective with roadmap
- `erk objective check <issue>` - Validate objective structure
- `erk objective list` - List all objectives
- `erk objective close <issue>` - Close completed objective
- `erk exec update-roadmap-step` - Update single step PR and status in both frontmatter and table
- `/erk:objective-update-with-landed-pr` - Full update after PR lands

## Implementation References

| File                                 | Purpose                        |
| ------------------------------------ | ------------------------------ |
| `objective_roadmap_shared.py`        | Core parser: `parse_roadmap()` |
| `objective_roadmap_frontmatter.py`   | Frontmatter parser/serializer  |
| `update_roadmap_step.py`             | Surgical PR cell update        |
| `objective-update-with-landed-pr.md` | Full-body update agent         |
| `objective_update_context.py`        | Context fetch for updates      |
| `check_cmd.py`                       | Objective validation           |

## See Also

- [Objective Roadmap Frontmatter](objective-roadmap-frontmatter.md) - YAML schema details
- [Objective Planning Patterns](objective-planning.md) - Creating plans from objectives
- [GitHub Metadata Blocks](../architecture/github-metadata-blocks.md) - Metadata block infrastructure
