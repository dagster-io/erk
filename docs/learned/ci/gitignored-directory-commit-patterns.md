---
title: CI Gitignored Directory Commit Patterns
read_when:
  - "working with .erk/impl-context/ in CI workflows"
  - "force-adding gitignored files in GitHub Actions"
  - "debugging why .erk/impl-context/ appears in PR diffs"
tripwires:
  - action: "committing .erk/impl-context/ without git add -f"
    warning: "The directory is gitignored. Use git add -f .erk/impl-context to force-add it. Without -f, git silently skips the directory."
    score: 5
---

# CI Gitignored Directory Commit Patterns

`.erk/impl-context/` is gitignored but needs temporary git tracking during CI workflows. This requires force-add and explicit cleanup.

## Three-Phase Lifecycle

### Phase 1: Force-Add During Setup

<!-- Source: .github/workflows/plan-implement.yml, Phase 1 setup step -->

The setup step creates the implementation context, force-adds it to git tracking, and pushes to the remote branch. `git add -f` overrides `.gitignore` to track the directory. This creates a committed snapshot that the implementation agent reads from.

### Phase 2: Remove Before Implementation

<!-- Source: .github/workflows/plan-implement.yml, cleanup step -->

The cleanup step in `plan-implement.yml` (lines 406-409 and similar patterns) uses `git rm -r --cached` to remove from git tracking while preserving files on disk. The implementation agent still reads the local files, but they no longer appear in the PR diff. This is idempotent — safe to run even if already cleaned up.

### Phase 3: Clean Up After Implementation

Same pattern as Phase 2, run as a safety net after implementation completes. Idempotent — safe to run even if Phase 2 already cleaned up.

## Key Commands

| Command                                           | Effect                                        |
| ------------------------------------------------- | --------------------------------------------- |
| `git add -f .erk/impl-context`                    | Force-add gitignored directory                |
| `git rm -r --cached .erk/impl-context/`           | Remove from tracking, keep on disk            |
| `git ls-files --error-unmatch .erk/impl-context/` | Check if directory is tracked (exit 1 if not) |

## Plan-Header Metadata Preservation

<!-- Source: src/erk/cli/commands/exec/scripts/ci_update_pr_body.py, plan-header error handling -->

When rewriting PR bodies in CI, the plan-header metadata block must be preserved. The error handling in `ci_update_pr_body.py` (around lines 266-277) validates that the plan-header metadata block exists, using a `UpdateError` discriminated union with a specific `plan-header-not-found` variant to signal metadata loss in previous CI steps.

## Agent Instruction Cross-References

The `pr-address` command is the only slash command that directly edits and commits `.erk/impl-context/` files. Line 209 of `.claude/commands/erk/pr-address.md` contains the `git add -f` note for plan-only PRs:

> **Note:** If any changed files are in `.erk/impl-context/` (plan-only PRs), use `git add -f` instead — the directory is gitignored.

Pattern: When a slash command touches gitignored paths, document the `git add -f` requirement directly in that command's instructions. Without this, agents waste turns discovering that regular `git add` silently skips the files.

**Real-world trigger:** PR #8544 (plan-only PR) caused the agent to waste 2 turns discovering `git add -f` was required.

## Related Documentation

- [Impl-Context Staging Directory](../planning/impl-context.md) — Full lifecycle of the staging directory
- [Planned PR Lifecycle](../planning/planned-pr-lifecycle.md) — How metadata blocks are managed
