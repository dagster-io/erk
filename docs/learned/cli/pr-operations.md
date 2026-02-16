---
title: "PR Operations: Duplicate Prevention and Detection"
read_when:
  - "creating PRs programmatically"
  - "implementing PR submission workflows"
  - "preventing duplicate PR creation"
tripwires:
  - action: "running gh pr create"
    warning: "Query for existing PRs first via `gh pr list --head <branch> --state all`. Prevents duplicate PR creation and workflow breaks."
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# PR Operations: Duplicate Prevention and Detection

## Why This Matters

Duplicate PRs break workflows in subtle ways. Multiple PRs for the same branch fragment review comments, trigger redundant CI runs, and create ambiguity about which PR is "real". The fix is simple but critical: **always query before creating**.

## The Core Pattern

Before creating a PR, query by branch name including ALL states:

```bash
gh pr list --head "$BRANCH_NAME" --state all
```

**Why `--state all`?** Without it, you only check open PRs. A closed or merged PR means "don't recreate this" — the user explicitly closed it or already landed it.

## Decision: Branch Query vs Title Search

<!-- Source: .claude/commands/erk/git-pr-push.md, Step 6.5 -->

Branch-based queries are precise and fast because GitHub indexes them. Title-based searches (`--search "Feature X in:title"`) are slow and unreliable — titles change, contain typos, and match unrelated PRs.

See the implementation pattern in `/erk:git-pr-push` (`.claude/commands/erk/git-pr-push.md`, Step 6.5).

## Gateway Layer: REST API vs gh CLI

<!-- Source: packages/erk-shared/src/erk_shared/gateway/github/real.py, RealGitHub.get_pr_for_branch -->

Erk's gateway layer uses the REST API directly via `gh api` for PR queries:

```bash
gh api "/repos/{owner}/{repo}/pulls?head={owner}:{branch}&state=all"
```

**Why REST instead of `gh pr list`?** The gateway preserves GraphQL quota for operations that don't have REST equivalents (review threads, timeline events). See `RealGitHub.get_pr_for_branch()` in `packages/erk-shared/src/erk_shared/gateway/github/real.py`.

The command layer uses `gh pr list` because simplicity matters more than quota optimization in one-off user commands.

## The Branch Name Must Match

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_for_plan.py, lines 88-99 -->

GitHub's PR query matches the **exact branch name** including owner prefix (`owner:branch`). If your branch naming changes (e.g., different timestamp suffixes for the same feature), each branch can have its own PR. This is intentional — erk branches are immutable once created.

The `erk exec get-pr-for-plan` script (see `src/erk/cli/commands/exec/scripts/get_pr_for_plan.py`) demonstrates fallback logic when `branch_name` is missing from plan metadata: it infers the branch from the current git context if it matches the plan's issue number prefix (`P{issue_number}-`).

## Integration: Plan Metadata and PR Discovery

Erk stores `branch_name` in plan-header metadata when a plan is submitted. This creates a durable link: issue → branch → PR. The full discovery strategy (including fallbacks when metadata is missing) is documented in `docs/learned/planning/pr-discovery.md`.

**Why store branch_name?** PR discovery is deterministic when you have the branch name. Without it, you resort to heuristics (searching commit messages, checking issue timelines) that may find the wrong PR or no PR at all.

## Update vs Create Decision Tree

When implementing PR submission:

1. Query for existing PR by branch (`gh pr list --head $BRANCH --state all`)
2. **If result is non-empty:**
   - PR exists (open, closed, or merged)
   - **Do not create** — either update the existing PR or exit with reference to it
3. **If result is empty:**
   - No PR exists for this branch
   - Safe to create with `gh pr create`

**Anti-pattern:** Catching `gh pr create` errors and retrying. The error happens after you've already created a duplicate. Query first, not after.

## Related Documentation

- `docs/learned/planning/pr-discovery.md` — Fallback strategies when branch_name is missing
- `docs/learned/architecture/github-cli-limits.md` — REST API alternatives for large PR operations
