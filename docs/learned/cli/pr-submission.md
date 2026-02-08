---
title: PR Submission Decision Framework
read_when:
  - "choosing between git-pr-push and pr-submit commands"
  - "understanding PR submission workflows"
  - "deciding whether to use Graphite or plain git"
last_audited: "2026-02-08"
audit_result: clean
tripwires:
  - "Before creating PRs, understand the workflow tradeoffs"
  - "PR validation rules apply to both workflows"
---

# PR Submission Decision Framework

Erk provides two PR submission workflows with fundamentally different design goals. Choosing the wrong one creates friction.

## The Core Question

**Do you need stack management?** Not "do you have stacks?" but "does this work benefit from Graphite's stack operations?"

### Use `/erk:git-pr-push` When

- **Remote execution context** — GitHub Actions workflows, CI environments where Graphite isn't available
- **Single-branch PRs** — no dependencies on other PRs, simple merge to main
- **Commit history preservation matters** — you want to keep granular commit messages intact
- **Graphite isn't installed** — bare git repos, lightweight environments

**Why:** This workflow uses only `git` + `gh` CLI. No stack metadata, no rebase operations, no external tooling dependencies.

### Use `/erk:pr-submit` When

- **Stacked PRs** — this PR depends on or blocks other PRs
- **Stack rebase is desired** — you want Graphite to rebase the entire stack after submission
- **Commit squashing is desired** — you want a single commit representing the entire feature
- **Local development environment** — Graphite is installed and configured

**Why:** This workflow delegates to `erk pr submit`, which uses Graphite's `gt submit` under the hood. It squashes commits and rebases the stack automatically.

## Workflow Differences

The two commands diverge in their operations:

| Decision Point    | git-pr-push                     | pr-submit                 |
| ----------------- | ------------------------------- | ------------------------- |
| Commit handling   | Preserves all commits           | Squashes to single commit |
| Stack operations  | None (standalone PR)            | Rebases entire stack      |
| Tool dependencies | git + gh CLI only               | Graphite required         |
| PR creation       | `gh pr create`                  | `gt submit`               |
| Execution context | Works anywhere git/gh installed | Requires Graphite setup   |

**Anti-pattern:** Using `/erk:pr-submit` in GitHub Actions — Graphite isn't available in CI environments. The command will fail during authentication checks.

**Anti-pattern:** Using `/erk:git-pr-push` for stacked PRs — you lose Graphite's stack management. Later stack operations will be confused by the missing metadata.

## PR Validation Rules

Both workflows must satisfy the same validation rules checked by `erk pr check`:

1. **Issue closing reference** — When `.impl/issue.json` exists, PR body must contain `Closes #N` (or `Closes owner/repo#N` for cross-repo plans)
2. **Checkout footer** — PR body must contain `erk pr checkout <pr-number>` command
3. **Branch/issue agreement** — Branch name pattern `P123-...` must match `.impl/issue.json` issue number

These rules are enforced by validation functions in the PR submission gateway:

<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_checkout_footer_for_pr -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/pr/submit.py, has_issue_closing_reference -->

See `has_checkout_footer_for_pr()` and `has_issue_closing_reference()` in `packages/erk-shared/src/erk_shared/gateway/pr/submit.py`.

**Why these rules exist:**

- **Issue closing** — Enables GitHub's auto-close on merge, maintains plan-to-PR traceability
- **Checkout footer** — Enables `erk pr checkout` command to work, provides remote execution context
- **Branch/issue agreement** — Prevents stale `.impl/` folders from creating wrong issue linkages

## Cross-Repo Plans

When `.impl/issue.json` contains a `plans_repo` field (e.g., `anthropics/erk-plans`), the closing reference format changes:

- **Same-repo:** `Closes #123`
- **Cross-repo:** `Closes anthropics/erk-plans#123`

<!-- Source: src/erk/cli/commands/exec/scripts/get_pr_body_footer.py, build_pr_body_footer -->

The footer generation logic handles this automatically via `build_pr_body_footer()` in the gateway layer.

## Implementation Notes

### Why git-pr-push Checks for Existing PRs

<!-- Source: .claude/commands/erk/git-pr-push.md, Step 6.5 -->

The git-pr-push workflow checks for existing PRs (Step 6.5 in the command spec) before attempting `gh pr create`. This prevents duplicate PR creation when:

- Agent re-runs the command after a failure
- User pushes additional commits and expects the existing PR to update
- Remote execution retries due to transient failures

**Without this check:** `gh pr create` would fail with "PR already exists for branch", requiring manual error recovery.

**With this check:** The workflow updates the existing PR via `git push` and reports the PR URL, behaving idempotently.

### Why Validation Runs After PR Creation

Both workflows run `erk pr check` after creating the PR, even though the PR is already public. This isn't validation-before-submission (which would be ideal), it's **auditing that the submission logic worked correctly**.

**What it catches:**

- Footer generation logic bugs (wrong PR number embedded)
- Issue reference extraction failures (`.impl/issue.json` wasn't read correctly)
- GitHub API quirks (PR body didn't save as expected)

**Anti-pattern:** Treating validation failures as user errors — these are system bugs. If `erk pr check` fails after a workflow completes, the workflow's PR construction logic is broken.

## Historical Context

The dual-workflow design exists because:

1. **Remote execution requirement** — GitHub Actions agents run erk commands but can't install Graphite (it's a proprietary tool requiring authentication)
2. **Stack management value** — Local development benefits from Graphite's stack operations for dependent PRs
3. **Commit history preferences** — Some users want granular commits (git-pr-push), others want squashed feature commits (pr-submit)

We tried unifying them with a `--no-stack` flag, but the behavioral differences (squashing, rebasing, tool dependencies) were too divergent. Separate commands make the tradeoffs explicit at invocation time.

## See Also

- [Git-PR-Push Command](.claude/commands/erk/git-pr-push.md) — Full command specification
- [PR-Submit Command](.claude/commands/erk/pr-submit.md) — Full command specification
- [PR Check Command](../cli/commands/pr-check.md) — Validation rules reference
