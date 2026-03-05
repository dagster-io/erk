# Plan: Fix planning/ docs terminology (Objective #8381, Nodes 6.1 + 6.2)

## Context

Objective #8381 standardizes "plan-as-PR" terminology across the codebase. Phases 1-5 fixed code, CLI help, commands, and exec scripts. Phase 6 targets documentation. Nodes 6.1 and 6.2 together cover all 19 `docs/learned/planning/` files.

The core change: replace "plan issue" with "plan" throughout, matching patterns established in prior PRs (#8382-#8580).

## Node 6.1: High-priority planning/ docs (4 files need fixes, 3 clean)

### 1. `docs/learned/planning/lifecycle.md` (5 instances)

- Line 10: "plan issue" → "plan"
- Line 101: `plan-issue-number` → `plan-number`
- Line 107: "plan issue was already created" → "plan was already created"
- Line 642: "plan issue link" → "plan link"
- Line 663: "plan issue is tracked" → "plan is tracked"
- Line 1044: "One-shot plan issue created" → "One-shot plan created"

### 2. `docs/learned/planning/session-deduplication.md` (1 instance)

- Line 18: "duplicate plan issues" → "duplicate plans"

### 3. `docs/learned/planning/pr-submission-patterns.md` (2 instances)

- Line 33: "duplicate plan issues" → "duplicate plans"
- Line 78: "plan issue to remain open" → "plan to remain open"

### 4. `docs/learned/planning/learn-workflow.md` (10 instances)

- Line 28: "plan issue for human review" → "plan for human review"
- Line 69: "parent plan issue number" → "parent plan number"
- Line 147: "learn plan issue" → "learn plan"
- Line 148: "plan issue is queued" → "plan is queued"
- Line 150: "plan issue" (x2) → "plan"
- Line 160: `--plan-issue` → `--learn-plan` (matches PR #8580 code change)
- Line 188: "learn plan issue is created" → "learn plan is created"
- Line 190: "plan issue" → "plan"
- Line 213: "created plan issue #N" → "created plan #N"
- Line 216: "plan issue or PR" → "plan"
- Line 240: "Parent plan issue number" → "Parent plan number"
- Line 252: "parent plan issue" → "parent plan"

### Already clean (no changes)

- `docs/learned/planning/workflow.md`
- `docs/learned/planning/one-shot-workflow.md`
- `docs/learned/planning/workflow-markers.md`

## Node 6.2: Remaining planning/ docs (7 files need fixes, 5 clean)

### 5. `docs/learned/planning/label-scheme.md` (~3 instances)

- "plan issues" → "plans" (including "Regular plan issues", "Learn plan issues")
- "creates a new issue" → "creates a new draft PR" (where referring to PlannedPRBackend)

### 6. `docs/learned/planning/metadata-block-fallback.md` (~4 instances)

- "plan issues split content" → "plans split content"
- "plan issue's metadata" → "plan's metadata"
- "Older issues" → "Older plans"
- "older erk-plan issues" → "older erk-plans"

### 7. `docs/learned/planning/learn-vs-implementation-plans.md` (~4 instances)

- "issue infrastructure" → "draft PR infrastructure"
- Clarify `learned_from_issue` is a metadata field name, not a storage mechanism reference

### 8. `docs/learned/planning/planned-pr-backend.md` (~5 instances)

- "Issue-based plans use issue numbers" → clarify as historical reference
- "plan-saved-issue marker" → update if marker name has changed in code
- Clean up legacy "issue-based" comparison language

### 9. `docs/learned/planning/plan-creation-pathways.md` (~2 instances)

- "issue-based plan storage path" → "legacy issue-based plan storage backend (deleted)"

### 10. `docs/learned/planning/plan-execution-patterns.md` (1 instance)

- read_when: "plan from a GitHub issue" → "plan from a GitHub draft PR"

### 11. `docs/learned/planning/metadata-field-workflow.md` (1 instance)

- read_when/title: "plan issue schema" → "plan metadata schema"

### Already clean (no changes)

- `docs/learned/planning/consolidation-labels.md`
- `docs/learned/planning/learn-plan-validation.md`
- `docs/learned/planning/branch-name-inference.md`
- `docs/learned/planning/learn-plan-metadata-fields.md`
- `docs/learned/planning/next-steps-output.md`

## Verification

1. Grep for remaining "plan.issue" in all 19 files: `grep -rn "plan.issue" docs/learned/planning/`
2. Verify no broken markdown links or formatting
3. Run `make fast-ci` to confirm nothing breaks
