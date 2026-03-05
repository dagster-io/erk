# Plan: Fix High-Priority Planning Docs Terminology

**Part of Objective #8381, Node 6.1**

## Context

Objective #8381 standardizes plan-as-PR terminology across the codebase. Plans are now stored as draft PRs, not GitHub issues. Phases 1–5 updated code, CLI help, exec scripts, skills, and commands. Phase 6 targets documentation in `docs/learned/`.

Node 6.1 covers the 7 highest-priority planning docs that still use stale "issue" terminology when referring to plans.

## Terminology Mapping

| Old Term | New Term | Notes |
|----------|----------|-------|
| "plan issue" | "plan" or "plan PR" | Context-dependent |
| "GitHub issue" (for plans) | "draft PR" or "plan PR" | |
| `<issue_number>` param | `<plan>` or `<plan-number>` | In docs/examples |
| `issue_number` field | `plan_number` or `plan_id` | In doc examples only |
| "issue number" (prose) | "plan number" | |

**Preserve as-is:** `learned_from_issue` (code field name), `erk-plan` label, `erk-objective` label, actual GitHub Issues concepts.

## Files to Modify (7 files)

### 1. `docs/learned/planning/lifecycle.md`
~18 instances. Heaviest file. Includes:
- Tripwire text referencing `gh issue create`
- `issue_number` field names in YAML examples
- `<issue_number>` command parameters
- Workflow concurrency group names
- Prose references to "plan issue"

### 2. `docs/learned/planning/workflow.md`
~4 instances:
- `<issue-number>` in command examples
- "GitHub issue" → "plan PR" for progress tracking
- Command parameter names

### 3. `docs/learned/planning/session-deduplication.md`
~1 instance:
- "duplicate plan issues" → "duplicate plans"

### 4. `docs/learned/planning/pr-submission-patterns.md`
~5 instances:
- "issue number" in tripwire warnings
- "GitHub issue" in creation context
- "plan issue to remain open" → "plan PR to remain open"

### 5. `docs/learned/planning/learn-workflow.md`
~16 instances. Second-heaviest:
- `<parent-issue-number>` command params
- `--plan-issue` flag references
- "plan issue" in prose throughout
- Field description comments
- TUI display text

### 6. `docs/learned/planning/one-shot-workflow.md`
~4 instances:
- `plan_issue_number` → `plan_number`
- "issue number" in prose
- "GitHub issue" → "GitHub PR"

### 7. `docs/learned/planning/workflow-markers.md`
~4 instances:
- Marker name `plan-saved-issue` → `plan-saved`
- Variable name `ISSUE_NUM` → `PLAN_NUM`
- "issue number" in prose

## Implementation Approach

Process files one at a time using Edit tool. For each file:
1. Read the file
2. Apply all terminology fixes via targeted edits
3. Preserve code field names that are actual identifiers (e.g., `learned_from_issue`)

**Order:** lifecycle.md → learn-workflow.md → pr-submission-patterns.md → workflow.md → one-shot-workflow.md → workflow-markers.md → session-deduplication.md (heaviest files first)

## Verification

1. Grep `docs/learned/planning/` for remaining "issue" references in the 7 files — confirm only legitimate uses remain (actual GitHub Issues concepts, code field names)
2. Run `erk docs check` if available to validate doc structure
3. Run fast CI to ensure no doc generation breaks
