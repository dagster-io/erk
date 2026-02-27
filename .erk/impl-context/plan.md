# Plan: Fix Plan-as-PR Terminology in Claude Code Commands (Phase 3)

Part of Objective #8381, Nodes 3.1 + 3.2 + 3.3

## Context

Objective #8381 standardizes "plan-as-PR" terminology across the codebase. Plans used to be GitHub Issues but are now draft PRs. Phases 1-2 and 4 are already done. Phase 3 covers 18 `.claude/commands/` files that still contain stale "plan issue" / "issue" terminology when referring to plans.

**Key constraint**: Exec script names (`get-issue-body`), marker names (`plan-saved-issue`), env vars (`$PLAN_ISSUE_NUMBER` in CI), and metadata field names (`objective_issue`) are **code contracts still in source** — leave these unchanged. Only fix **user-facing text**: descriptions, examples, error messages, URL examples, variable name placeholders, and conceptual framing.

JSON output keys from `plan_save.py` are already `plan_number`, `plan_url`, `plan_backend` — commands should reference these, not `issue_number`.

## Changes

### Node 3.1 — High-Severity (4 files)

**`.claude/commands/erk/replan.md`** — Heaviest file (~20 changes)
- URL examples: `/issues/2521` → `/pull/2521` (lines 16, 29)
- Agent prompt: `ISSUES:` → `PLANS:`, "multiple issues" → "multiple plans", "issues are closed" → "plans are closed" (lines 55-81)
- `gh issue comment` → `gh pr comment` (line 226)
- `gh issue view` → `gh pr view` (lines 433, 449)
- `original_issue_number` → `original_plan_number` (line 297)
- `new_issue_number` → `new_plan_number` (lines 397-401)
- Keep `objective_issue` field name (matches code)

**`.claude/commands/local/audit-plans.md`** — ~10 changes
- "erk-plan issues" → "open plans" (line 22)
- `| Issue |` table headers → `| Plan |` (lines 121, 129, 137, 145, 153)
- "auto-close any issues" → "auto-close any plans" (line 162)
- `gh api .../issues/<N>` close → `gh pr close <N>` (line 176)
- `<issue-number>` → `<plan-number>` (line 216)

**`.claude/commands/erk/learn.md`** — ~15 changes
- "Save plan as a new GitHub issue" → "Save plan as a draft PR" (lines 34, 44)
- "if the issue is a learn plan" → "if the plan is a learn plan" (lines 49, 62)
- `issue_number` → `plan_number` in output references (lines 288, 689, 708)
- `issue_url` → `plan_url` (lines 713, 794)
- "Learn Plan Issue" → "Learn Plan PR" in heading (line 717)
- Keep exec script names and `--issue` flags (code contracts)
- Keep `learn_plan_issue` field name (code contract)

**`.claude/commands/local/plan-update.md`** — 1 change
- URL example: `/issues/42` → `/pull/42` (line 26)

### Node 3.2 — Medium-Severity (4 files)

**`.claude/commands/erk/plan-save.md`** — 0 real changes
- `plan-saved-issue` marker name matches code — leave as-is
- File is already clean

**`.claude/commands/erk/one-shot-plan.md`** — ~3 changes
- Keep `$PLAN_ISSUE_NUMBER` (CI workflow contract in one-shot.yml)
- "Fall back to creating a new issue" → "Fall back to creating a new draft PR" (line 58)
- Add comment noting `$PLAN_ISSUE_NUMBER` is a legacy env var name

**`.claude/commands/erk/plan-implement.md`** — ~7 changes
- argument-hint: `issue-number-or-url-or-path` → `plan-number-or-url-or-path` (line 3)
- "An issue number" → "A plan number" (line 21)
- URL example: `/issues/2521` → `/pull/2521` (line 44)
- "capture the issue number" → "capture the plan number" (line 86)
- `issue_number` → `plan_number` in parse instructions (lines 92, 95)
- "Fetching plan from issue #X" → "Fetching plan #X" (line 204)

**`.claude/commands/erk/pr-dispatch.md`** — 1 change
- Clarify issues URL as legacy format (line 23)

### Node 3.3 — Low-Severity (10 files)

**`.claude/commands/local/check-relevance.md`** — ~5 changes
- "by issue number" → "by number" (line 12)
- "plan issue body" → "plan body" (line 55)
- "new issue" → "new plan" for follow-ups (lines 211, 230)
- Follow-up creation via `gh api .../issues` → note this should be a plan

**`.claude/commands/local/replan-learn-plans.md`** — ~7 changes
- "open issues" → "open plans" (line 27)
- "filter out any issues" → "filter out any plans" (lines 43, 53)
- "erk-learn issues" → "erk-learn plans" (lines 61, 67)
- `| Issue |` → `| Plan |` (lines 82, 103)
- `issue_number` → `plan_number` (line 126)

**`.claude/commands/erk/objective-update-with-closed-plan.md`** — ~4 changes
- "Plan issue number" → "Plan number" (line 29)
- "Objective issue number" → "Objective number" (line 30)
- "Plan issue body" → "Plan body" (line 41)
- `gh issue view` → `gh pr view` when referencing plans (line 63)

**`.claude/commands/erk/system/objective-update-with-landed-pr.md`** — ~3 changes
- "Objective issue number" → "Objective number" (line 30)
- "Plan issue number" → "Plan number" (line 32)
- "Plan issue body" → "Plan body" (line 54)

**`.claude/commands/erk/objective-plan.md`** — ~8 changes
- argument-hint: `issue-number-or-url` → `objective-number-or-url` (line 3)
- "an issue number" → "an objective number" (line 26)
- `<issue-number>` → `<objective-number>` where referring to objectives (lines 31, 44, 145, 198)
- `plan-issue-number` → `plan-number` (line 65)
- "erk-plan issue" → "plan PR" (line 110)
- Keep `objective_issue` field name and `get-issue-body` script name
- Keep `"issue_number"` in JSON examples where it matches actual API output — verify if API was updated

**`.claude/commands/erk/system/objective-plan-node.md`** — ~10 changes
- argument-hint: `<issue-number>` → `<objective-number>` (line 3)
- "Issue number" → "Objective number" (line 29)
- `<issue-number>` → `<objective-number>` throughout (lines 19, 32, 48, 55, 86, 97, 113)
- "erk-plan issue" → "plan PR" (line 51)
- `<new-issue-number>` → `<new-plan-number>` (line 170)
- Error table: "issue number" → "objective number", "Issue not found" → "Objective not found" (lines 190, 192)

**`.claude/commands/erk/land.md`** — ~2 changes
- `"issue_number"` → `"plan_number"` in JSON example (line 104) — if API contract matches
- "objective issue number" → "objective number" (line 109)

**`.claude/commands/local/objective-view.md`** — ~8 changes
- `<issue_number>` → `<objective_number>` (lines 12, 21, 25, 31, 51, 59, 75)
- "Issue number required" → "Objective number required" (line 21)
- "issue body" → "objective body" (line 36)
- "erk-plan issues" → "plans" (line 88)
- "Issue not found" → "Objective not found" (line 221)

**`.claude/commands/erk/objective-create.md`** — ~3 changes
- "Write to Plan File and Create Issue" → "Write to Plan File and Create Objective" (line 259)
- "Create the GitHub issue" → "Create the objective" (lines 286, 292)
- "Issue number" → "Objective number" (line 316)

**`.claude/commands/local/incremental-plan-mode.md`** — 0 changes (already clean)

## Verification

1. Grep for remaining stale terms across all modified files:
   - `grep -n "plan issue\|plan issues\|erk-plan issue" .claude/commands/**/*.md`
   - `grep -n "issue_number\|issue_url" .claude/commands/**/*.md` (filter out exec script names and code contracts)
2. Run `make fast-ci` to ensure no formatting/lint issues
3. Spot-check that exec script names, marker names, and metadata field names were NOT changed
