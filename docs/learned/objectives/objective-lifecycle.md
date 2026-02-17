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
  - action: "updating roadmap step in only one location (frontmatter or table)"
    warning: "Must update both frontmatter AND markdown table during the dual-write migration period. Use update-objective-node which handles both atomically."
last_audited: "2026-02-16 04:53 PT"
audit_result: clean
---

# Objective Lifecycle

This document describes the complete lifecycle of objective issues from creation to closure, including all mutation paths and data flows.

## Overview

Objectives are GitHub issues with the `erk-objective` label that track multi-plan work through a roadmap structure. The roadmap exists in two forms:

1. **Source of truth**: YAML frontmatter in `<!-- erk:metadata-block:objective-roadmap -->` blocks (in issue body)
2. **Rendered view**: Markdown table in the objective-body comment (for human readability)

All objectives use v2 YAML format. `parse_roadmap()` returns a legacy-format error for non-v2 content. Mutations update both the YAML frontmatter and the rendered table atomically via `update-objective-node`.

## Objective States

Objectives have an implicit state machine based on roadmap step completion:

```
Created → Active → Complete → Closed
```

- **Created**: Objective exists with roadmap, no steps done
- **Active**: At least one step in progress, planning, or done
- **Complete**: All steps are done or skipped (terminal step statuses)
- **Closed**: Issue is closed (manually or automatically)

### Step-Level States

Individual roadmap steps follow this lifecycle:

```
pending → planning → in_progress → done
                                  → skipped
          → blocked (from any non-terminal state)
```

- **pending**: Work not started
- **planning**: Step dispatched for autonomous planning (draft PR created via `erk objective plan`)
- **in_progress**: Active implementation underway
- **done**: PR landed
- **blocked**: External dependency prevents progress
- **skipped**: Step determined unnecessary

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

schema_version: "2"
steps:

- id: "1.1"
  description: "Add user model"
  status: "pending"
  plan: null
  pr: null
- id: "1.2"
  description: "Add JWT library"
  status: "pending"
  plan: null
  pr: null
- id: "2.1"
  description: "Implement login"
  status: "pending"
  plan: null
  pr: null

---

<!-- /erk:metadata-block:objective-roadmap -->

## Roadmap

[same markdown table as above]
```

## Reading

All roadmap reads go through `parse_roadmap(body: str)` in `erk_shared.gateway.github.metadata.roadmap` (`packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py`).

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
  │  └─ Invalid → Return ([], [legacy_format_error])
  │
  └─ No metadata block → Return ([], [legacy_format_error])
```

There is no table-parsing fallback. Non-v2 content returns an empty phases list with a legacy format error message directing users to recreate the objective.

### Status Resolution

Status comes directly from the YAML `status` field in frontmatter — no inference from plan/PR columns.

- Phase names extracted from markdown headers via `_enrich_phase_names()` (not stored in YAML)
- Phase membership derived from step ID prefix (e.g., "1.2" → phase 1)

## Mutations

Mutations update YAML frontmatter in the issue body (source of truth) and the markdown table in the objective-body comment (rendered view). Both are updated atomically by `update-objective-node`.

### Mutation Sites

| Site                                    | Type      | Trigger                                         | Updates                          | Frontmatter-Aware?              |
| --------------------------------------- | --------- | ----------------------------------------------- | -------------------------------- | ------------------------------- |
| `update-objective-node.py`              | Surgical  | `erk exec update-objective-node` or `plan-save` | YAML frontmatter + table comment | Yes (this plan)                 |
| `objective-update-with-landed-pr`       | Full-body | After landing PR                                | Roadmap + prose sections         | Yes (this plan)                 |
| `plan-save.md` Step 3.5                 | Indirect  | Creating plan from objective                    | Calls `update-objective-node`    | Inherits                        |
| `check_cmd.py` / `validate_objective()` | Read-only | `erk objective check`                           | N/A (reads only)                 | Inherits from `parse_roadmap()` |
| `objective_fetch_context.py`            | Read-only | Fetch context for updates                       | N/A (reads only)                 | Inherits from `parse_roadmap()` |

### Surgical Update: `update-objective-node`

**Path**: `src/erk/cli/commands/exec/scripts/update_objective_node.py`

**What it does**: Updates a single step's PR reference and recomputes status.

**Mutation flow**:

1. Fetch issue body
2. Check for `objective-roadmap` metadata block
3. Parse YAML frontmatter, find step by ID
4. Update `plan`/`pr` fields and recompute `status`
5. Serialize back to YAML and replace metadata block in body
6. Write updated body to GitHub
7. Also update markdown table in objective-body comment (v2 rendered view)

**Usage**:

```bash
erk exec update-objective-node 6423 --node 1.3 --pr "plan #6464"
erk exec update-objective-node 6423 --node 1.3 --pr "#6500"
erk exec update-objective-node 6423 --node 1.3 --pr ""  # Clear
```

**Status computation** (table mode):

- `pr` starts with `#` → status = `done`
- `pr` starts with `plan #` → status = `in_progress`
- `pr` is empty → status = `pending`

### Full-Body Update: `objective-update-with-landed-pr`

**Path**: `.claude/commands/erk/objective-update-with-landed-pr.md`

**What it does**: Updates objective after landing a PR. Marks steps as done, posts action comment, reconciles stale prose sections.

**Mutation flow**:

1. Determine which steps the PR completed (compare plan to roadmap)
2. Compose action comment with summary and lessons learned
3. **Compose updated objective body:**
   - Parse YAML frontmatter
   - Update relevant step(s): set `pr: "#<number>"` and `status: "done"`
   - Serialize updated YAML and replace metadata block
   - Also update markdown table in objective-body comment
   - Reconcile stale prose sections (Design Decisions, Implementation Context)
4. Post action comment to GitHub
5. Write updated body to GitHub
6. Check if all steps are done/skipped → close objective if complete

**Agent workflow**: Single-agent pattern. Agent fetches context, then performs all updates directly (roadmap steps, prose reconciliation, action comment, validation).

### Indirect Updates

#### `plan-save.md` Step 3.5

When saving a plan that's part of an objective:

- Calls `erk exec update-objective-node <objective> --node <step-id> --pr "plan #<plan-number>"`
- Inherits frontmatter support from `update-objective-node`

## Frontmatter Format

All objectives use v2 YAML frontmatter. Legacy table-only objectives are no longer supported by the parser.

### Frontmatter Schema

```yaml
---
schema_version: "2"
steps:
  - id: "1.1" # Required: step identifier
    description: "..." # Required: human-readable description
    status: "pending" # Required: pending|planning|done|in_progress|blocked|skipped
    plan: null # Optional: null or string like "#6464" (plan issue number)
    pr: null # Optional: null or string like "#123" (landed PR number)
---
```

**Design decisions**:

- **Flat list**: Steps are stored flat, phase membership derived from ID prefix
- **No phase names**: Phase names live only in markdown headers (extracted at read time)
- **Schema versioning**: `schema_version` for future evolution
- **Explicit status**: No inference in frontmatter (unlike tables)

### Frontmatter and Table Relationship

- **Frontmatter** (in issue body) = source of truth for step data
- **Table** (in objective-body comment) = rendered view for human readability
- Mutations update both atomically via `update-roadmap-step`
- Reads use frontmatter only — table is never parsed

## Body Reconciliation

Objective body sections fall into three tiers based on how they're updated:

| Tier             | Sections                                                    | Owner             | Updated When                      |
| ---------------- | ----------------------------------------------------------- | ----------------- | --------------------------------- |
| **Mechanical**   | Roadmap status/PR cells                                     | Exec commands     | Plan assigned / PR landed         |
| **Reconcilable** | Design Decisions, Implementation Context, step descriptions | LLM agent         | After PR overrides what's written |
| **Immutable**    | Exploration Notes                                           | Agent at creation | Never (historical artifact)       |

### When Reconciliation Happens

1. **After every PR landing** (primary trigger): The `objective-update-with-landed-pr` agent performs prose reconciliation after mechanical step updates. It compares the objective body against what the PR actually implemented and corrects stale information.

2. **At next-step pickup** (lighter touch): When `objective-plan` runs, the agent scans the objective body for context that may be stale from other work in the codebase.

### What the Agent Checks

The agent reads the objective body (post-mechanical-update) and the PR title/description/plan, looking for:

- **Decision overrides**: Objective says one approach, PR implemented another
- **Scope changes**: Step description doesn't match what was actually built
- **Architecture drift**: Implementation Context describes files/patterns that moved or changed
- **Constraint invalidation**: Requirements that are no longer valid
- **New discoveries**: Insights that affect future steps

### How Reconciliation Is Reported

Action comments gain an optional **Body Reconciliation** subsection (after Roadmap Updates) documenting what changed. If nothing is stale, the subsection is omitted entirely.

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
│ update-objective-node: set pr="plan #N"                    │
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
│ - Reconcile stale prose sections                         │
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

| Consumer                     | Purpose                         |
| ---------------------------- | ------------------------------- |
| `check_cmd.py`               | Validate objective structure    |
| `objective_fetch_context.py` | Fetch objective/plan/PR context |
| `objective_list.py`          | List all objectives             |
| TUI viewers                  | Display objective state         |

All read-only consumers use `parse_roadmap()` which reads v2 YAML frontmatter.

## Related Commands

- `erk objective create` - Create new objective with roadmap
- `erk objective check <issue>` - Validate objective structure
- `erk objective list` - List all objectives
- `erk objective close <issue>` - Close completed objective
- `erk exec update-objective-node` - Update single step PR and status in both frontmatter and table
- `/erk:objective-update-with-landed-pr` - Full update after PR lands

## Implementation References

| File                                                                    | Purpose                        |
| ----------------------------------------------------------------------- | ------------------------------ |
| `packages/erk-shared/src/erk_shared/gateway/github/metadata/roadmap.py` | Core parser: `parse_roadmap()` |
| `src/erk/cli/commands/exec/scripts/update_objective_node.py`            | Surgical PR cell update        |
| `.claude/commands/erk/objective-update-with-landed-pr.md`               | Full-body update agent         |
| `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`          | Context fetch for updates      |
| `src/erk/cli/commands/objective/check_cmd.py`                           | Objective validation           |

## See Also

- [Objective Roadmap Frontmatter](objective-roadmap-frontmatter.md) - YAML schema details
- [Objective Planning Patterns](objective-planning.md) - Creating plans from objectives
- [GitHub Metadata Blocks](../architecture/github-metadata-blocks.md) - Metadata block infrastructure
