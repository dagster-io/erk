# Plan: Phase 3 — Fix Slash Command Terminology (Objective #8381)

## Context

Objective #8381 standardizes "plan-as-PR" terminology across the codebase. Phase 1 (CLAUDE.md/AGENTS.md) landed in PR #8382. Phase 2.1 is in progress (#8383). This plan covers **Phase 3 (nodes 3.1, 3.2, 3.3)**: fixing all slash command `.md` files in `.claude/commands/`.

The core change: replace "issue" with "plan" or "draft PR" when referring to erk plans. Plans were originally stored as GitHub issues but now use draft PRs.

## Critical Constraint: Prose-Only Changes

Many CLI flags, env vars, and command names still use "issue" in actual code (renaming happens in Phases 4-5). We must **NOT change** any of these:

| Keep As-Is | Reason |
|---|---|
| `--issue` flag on `setup-impl` | Actual CLI flag (Phase 4) |
| `$PLAN_ISSUE_NUMBER` env var | Still used in CI (Phase 5) |
| `objective_issue` field | Actual JSON field name |
| `get-issue-body` command | Actual exec script name |
| `plan-saved-issue` marker | Actual marker name |
| `issue_number` JSON field | Still output by some scripts |
| `gh issue comment`, `gh api .../issues/` | GitHub API (never changes) |
| `erk-plan`, `erk-learn` labels | Label names (never changes) |

**Only change prose**: descriptions, section titles, error messages, comments.

## Changes by File

### Phase 3.1 — High Severity

#### 1. `.claude/commands/erk/replan.md`
- Line 2: description `"erk-plan issue"` → `"plan"`
- Line 3: argument-hint `<issue-number-or-url>` → `<plan-number-or-url>`
- Line 8: `"erk-plan issue(s)"` → `"plan(s)"`
- Line 24: section title `"Parse Issue References"` → `"Parse Plan References"`
- Lines 28, 31, 33: `"issue number(s)"` → `"plan number(s)"`
- Line 89: error `"Issue #<number> is not an erk plan issue"` → `"Plan #<number> is not a valid plan"`
- Line 93: error `"Issue #<number> not found"` → `"Plan #<number> not found"`
- Line 246: `"new plan issue"` → `"new plan"`
- Line 387: `"new GitHub issue"` → `"new plan"`
- Success/error messages at end of file: `"Issue"` → `"Plan"` throughout

#### 2. `.claude/commands/local/audit-plans.md`
- Line 2: description `"erk-plan issues"` → `"plans"`
- Line 7: `"erk-plan issues"` → `"plans"`
- Line 47: `"Get issue body"` → `"Get plan body"`
- Line 189: `"in issue body"` → `"in the plan body"`

#### 3. `.claude/commands/erk/learn.md`
- Line 58: error `"Issue #<issue-number>"` → `"Plan #<plan-number>"`
- Lines 314, 431, 470: `"title from plan issue"` → `"title from the plan"`
- Lines 727, 743: `"learn plan issue"` → `"learn plan"`

#### 4. `.claude/commands/local/plan-update.md`
- Line 2: description `"plan issue"` → `"plan"`
- Lines 22-30: `"issue number"` → `"plan number"` (section title + 3 prose instances)

### Phase 3.2 — Medium Severity

#### 5. `.claude/commands/erk/plan-save.md`
- **Remove line 25**: entire issue backend description (`"Issue backend (PLAN_BACKEND = "github")..."`)
- **Line 27**: `"same for both backends"` → `"includes"` (remove "both backends" framing)
- **Line 104**: remove conditional, simplify to `"Close draft PR #<plan_number>"`
- **Lines 152-155**: remove `"Header (both backends):"` label; simplify conditional to just `"draft PR"`
- **Remove lines 210-224**: entire `"github"` backend output block
- **Lines 240, 242, 248**: `"issue number"` → `"plan number"` (3 instances in Session Tracking section)

#### 6. `.claude/commands/erk/one-shot-plan.md`
- Line 2: description `"GitHub issue"` → `"draft PR"`
- Line 7: `"GitHub issue"` → `"draft PR"`
- Line 50: `"skeleton plan issue"` → `"skeleton plan"`
- Keep `$PLAN_ISSUE_NUMBER` references as-is (actual env var)

#### 7. `.claude/commands/erk/plan-implement.md`
- Line 2: description `"GitHub issue, file path"` → `"GitHub, file path"`
- Line 30: comment `"issue #2521"` → `"plan #2521"`
- Line 54: `"GitHub issue/PR (draft-PR or issue-based)"` → `"GitHub (draft PR)"`
- Line 65: remove `gh issue view` fallback, simplify to just `gh pr view`
- Keep all `--issue` flag references as-is (actual flag)

#### 8. `.claude/commands/erk/pr-dispatch.md`
- Lines 9, 13: `"GitHub issue"` → `"plan"`
- Line 14: `"issue number"` → `"plan number"`
- Line 23: pattern label `"Issue:"` → `"Plan:"`
- Line 24: `"Issue URL"` → `"Plan URL"`
- Lines 26, 30: `"issue number"` → `"plan number"`
- Line 32: placeholder `<issue_number>` → `<plan_number>`
- Line 46: error `"No GitHub issue found"` → `"No plan found"`
- Line 47: `"validates the issue"` → `"validates the plan"`
- Keep `plan-saved-issue` marker name as-is

### Phase 3.3 — Low Severity

#### 9. `.claude/commands/erk/objective-plan.md`
- Line 17: `"issue reference"` → `"objective reference"`
- Line 42: `"issue reference"` → `"objective reference"`
- Line 62: `"plan issue found"` → `"plan found"`
- Line 91: `"plan #<plan-issue>"` → `"plan #<plan-number>"`

#### 10. `.claude/commands/local/check-relevance.md`
- Lines 12, 14: `"plan issue"` → `"plan"`
- Line 28: `"Treat as plan issue"` → `"Treat as plan"`

#### 11. `.claude/commands/erk/land.md`
- Line 77: `"plan issue number"` → `"plan number"`
- Line 174: `"Plan issue not found"` → `"Plan not found"`

#### 12. `.claude/commands/local/incremental-plan-mode.md`
- Lines 21, 53: `"save as GitHub issue?"` → `"save to GitHub?"`
- Line 100: `"skips issue creation"` → `"skips saving to GitHub"`

#### 13. `.claude/commands/local/replan-learn-plans.md`
- Line 7: `"erk-learn plan issues"` → `"erk-learn plans"`
- Line 135: `"issue numbers"` → `"plan numbers"`
- Line 197: `"erk-plan issues"` → `"plans"`

#### Clean files (no changes):
- `objective-create.md`, `objective-update-with-closed-plan.md`, `objective-update-with-landed-pr.md`, `objective-view.md`

## Verification

After all edits:

1. **Grep for stale prose** — remaining "issue" hits should only be interface references (flags, fields, commands, API paths, labels)
2. **Grep plan-save.md for issue backend** — confirm zero hits for `"github".*backend` or `issue backend`
3. **Spot-check cross-references** — ensure `/erk:plan-save`, `/erk:replan` etc. still resolve

## Execution Order

1. Phase 3.1 (replan.md → audit-plans.md → learn.md → plan-update.md)
2. Phase 3.2 (plan-save.md → one-shot-plan.md → plan-implement.md → pr-dispatch.md)
3. Phase 3.3 (objective-plan.md → check-relevance.md → land.md → incremental-plan-mode.md → replan-learn-plans.md)
4. Verification grep passes
5. CI check
