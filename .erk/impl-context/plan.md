# Documentation Plan: Fix learn skill to display draft PR vs issue based on plan backend

## Context

This PR fixes a UX inconsistency in the learn workflow where the skill always referred to saved plans as "issues" even when they were saved as draft PRs. Users running `/erk:learn` on draft-PR-backed plans saw confusing terminology ("issue #123" instead of "draft PR #123") and the "Review in browser" action ran the wrong `gh` subcommand.

The fix introduces backend-aware display logic: Learn now reads additional fields (`plan_backend`, `title`, `issue_url`) from `erk exec plan-save` JSON output, conditionally displays "draft PR" or "issue" based on the backend, and routes browser actions to the correct GitHub CLI command (`gh pr view` vs `gh issue view`).

This establishes a reusable pattern for any slash command that references plans in its output. The pattern is cross-cutting: `/erk:plan-submit`, TUI plan actions, and future commands opening plans in browser all need the same conditional routing logic. Documenting this pattern prevents future bugs where developers assume all plans are issues.

## Raw Materials

No gist URL was provided for this learn session.

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score 2-3)| 1     |

## Documentation Items

### HIGH Priority

#### 1. GitHub CLI routing tripwire

**Location:** `docs/learned/commands/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7754]

**Draft Content:**

```markdown
**opening a plan URL in browser without checking plan_backend** -> Draft-PR plans use `gh pr view`, issue-based plans use `gh issue view`. Parse `plan_backend` from plan-save JSON output to route correctly. Wrong command produces confusing 404 errors.
```

This tripwire is critical because the failure mode is silent and confusing: `gh issue view` on a PR number produces an unhelpful error, and developers may not realize the issue is command routing rather than permissions or API problems.

---

#### 2. Update learn command documentation

**Location:** `.claude/commands/erk/learn.md`
**Action:** UPDATE
**Source:** [PR #7754]

**Draft Content:**

The learn command already contains the implementation. This item validates that Step 7 and Step 10 are correctly documented inline:

- **Step 7**: Parse `plan_backend`, `title`, and `issue_url` from `erk exec plan-save` JSON output (not just `issue_number`)
- **Step 10**: Conditionally display "draft PR" or "issue" in success message and post-learn menu; route "Review in browser" to correct `gh` subcommand

No external documentation change needed - the command itself IS the documentation. This item confirms the inline changes are complete.

---

#### 3. Update learn workflow documentation

**Location:** `docs/learned/planning/learn-workflow.md`
**Action:** UPDATE
**Source:** [PR #7754]

**Draft Content:**

Add a subsection under "The Learn Flow" or "Related Commands" documenting backend-aware display:

```markdown
## Backend-Aware Display

When learn saves a plan, it reads additional fields from the `plan-save` JSON output to display the correct terminology:

| Field | Purpose |
|-------|---------|
| `plan_backend` | Determines "draft PR" vs "issue" display text |
| `title` | Shows the plan title in success message |
| `issue_url` | Direct link for browser actions |

The post-learn menu routes "Review in browser" to the correct GitHub CLI command based on `plan_backend`:
- `draft_pr` -> `gh pr view <number>`
- (other/empty) -> `gh issue view <number>`

<!-- Source: .claude/commands/erk/learn.md, Step 7 and Step 10 -->
See Steps 7 and 10 in the learn command for implementation details.
```

---

#### 4. Fix line-number source pointers

**Location:** `docs/learned/integrations/github-review-decision.md`
**Action:** UPDATE_REFERENCES
**Source:** [PR #7754 - audit-pr-docs bot]

**Cleanup Instructions:**

This is a pre-existing issue flagged by the audit-pr-docs bot during review, not introduced by this PR. The document contains line-number source pointers (e.g., `lifecycle.py:61-140`) that drift as code evolves.

Convert all line-number references to name-based source pointers:
- Find: `lifecycle.py:61-140` (or similar line-range patterns)
- Replace with: `lifecycle.py, ClassName.method_name` format
- Follow the two-part format from `docs/learned/documentation/source-pointers.md`

---

### MEDIUM Priority

#### 5. Plan-save JSON output schema

**Location:** `docs/learned/planning/plan-save-output-schema.md`
**Action:** CREATE
**Source:** [PR #7754]

**Draft Content:**

```markdown
---
title: Plan-Save Output Schema
read_when:
  - consuming output from erk exec plan-save
  - implementing commands that display plan information
  - routing GitHub CLI commands based on plan type
tripwires:
  - action: "parsing plan-save JSON output"
    warning: "plan_backend field determines draft_pr vs issue. Missing field means legacy issue-based plan."
---

# Plan-Save Output Schema

The `erk exec plan-save` command outputs JSON with fields consumed by multiple commands. This document defines the shared contract.

## Schema

| Field | Type | Description |
|-------|------|-------------|
| `issue_number` | integer | GitHub issue or PR number |
| `issue_url` | string | Direct URL to the issue or PR |
| `title` | string | Plan title |
| `plan_backend` | string | `"draft_pr"` for draft PRs, empty/missing for issues |

## Consumers

Commands that parse this output:
- `/erk:learn` - displays success message and routes browser action
- `/erk:plan-save` - returns result to parent workflow

## Backend Detection

```python
# Pattern for routing based on backend
if plan_backend == "draft_pr":
    # Use gh pr view
else:
    # Use gh issue view (default for legacy plans)
```

<!-- Source: src/erk/cli/commands/exec/scripts/plan_save.py -->
See the JSON assembly in plan_save.py for the authoritative implementation.
```

---

#### 6. Backend-aware display pattern

**Location:** `docs/learned/commands/backend-aware-display.md`
**Action:** CREATE
**Source:** [PR #7754]

**Draft Content:**

```markdown
---
title: Backend-Aware Display Pattern
read_when:
  - displaying plan information in command output
  - routing GitHub CLI commands based on plan type
  - implementing commands that reference plans
tripwires:
  - action: "displaying plan references without checking backend"
    warning: "Plans can be draft PRs or issues. Check plan_backend to display correct terminology and route gh commands correctly."
---

# Backend-Aware Display Pattern

Commands that reference plans in their output should conditionally display "draft PR" or "issue" based on the plan's storage backend.

## Pattern Elements

1. **Parse additional fields**: Read `plan_backend`, `title`, `issue_url` from exec script JSON output
2. **Conditional text**: Display "draft PR #N" vs "issue #N" based on backend
3. **Correct routing**: Use `gh pr view` for draft PRs, `gh issue view` for issues

## Example Implementation

In slash commands, use conditional interpolation:

```
<"draft PR" if plan_backend=="draft_pr", else "issue">
```

For browser actions:

```bash
# Draft PR backend
gh pr view <number> --web

# Issue backend (default)
gh issue view <number> --web
```

## Commands Using This Pattern

- `/erk:learn` - post-save success message and review action
- TUI plan actions - dashboard columns (see dashboard-columns.md)
- Future: `/erk:plan-submit` should adopt this pattern

<!-- Source: .claude/commands/erk/learn.md, Steps 7 and 10 -->
See the learn command for the canonical implementation.
```

---

## Contradiction Resolutions

No contradictions detected. Existing documentation is consistent with the changes in this PR.

## Stale Documentation Cleanup

### 1. Line-number source pointers in github-review-decision.md

**Location:** `docs/learned/integrations/github-review-decision.md`
**Action:** UPDATE_REFERENCES
**Phantom References:** Line-number references like `lifecycle.py:61-140`
**Cleanup Instructions:** Convert to name-based source pointers following `docs/learned/documentation/source-pointers.md` format. This is a pre-existing issue flagged by audit-pr-docs bot, not introduced by this PR.

## Prevention Insights

### 1. Inconsistent terminology between backends

**What happened:** The learn skill displayed "issue" for all saved plans, even when the underlying storage was a draft PR.
**Root cause:** Original implementation only read `issue_number` from plan-save output, not `plan_backend`.
**Prevention:** When consuming output from exec scripts that support multiple backends, always check for and handle the backend discriminator field.
**Recommendation:** TRIPWIRE (already included as HIGH priority item #1)

## Tripwire Candidates

### 1. GitHub CLI routing based on plan backend

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before opening a plan in browser with gh commands
**Warning:** Draft-PR plans use `gh pr view`, issue-based plans use `gh issue view`. Check `plan_backend` field from plan-save output to route correctly. Wrong command produces confusing errors.
**Target doc:** `docs/learned/commands/tripwires.md`

This is tripwire-worthy because:
- **Non-obvious**: Not immediately clear from code that different `gh` subcommands are needed for draft PRs vs issues
- **Cross-cutting**: Applies to any command that opens plans in browser (learn, plan-submit, TUI actions)
- **Silent failure**: Using wrong `gh` subcommand produces cryptic "not found" errors that don't point to the actual problem

Without this tripwire, future developers implementing plan browser actions will likely assume all plans are issues and introduce the same bug this PR fixes.

## Potential Tripwires

### 1. Line-number source pointers in documentation

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** Flagged by audit-pr-docs bot on this PR. Validates existing guidance in source-pointers.md but doesn't quite meet threshold because:
- Existing documentation already covers this (`source-pointers.md`)
- Violation doesn't break functionality, just creates maintenance burden
- audit-pr-docs bot catches these at PR time

Could be promoted if bot catches fail to prevent repeated violations, but current enforcement seems adequate.
