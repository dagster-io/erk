---
title: PR Rewrite Command
read_when:
  - "using or modifying erk pr rewrite"
  - "understanding the PR rewrite pipeline phases"
  - "working with squash, commit message generation, or PR updating"
tripwires:
  - action: "implementing a new `erk pr` command"
    warning: "Compare feature parity with `submit_pipeline.py`. Check: issue discovery, closing reference preservation, learn plan labels, footer construction, and plan details section. Use shared utilities from `shared.py` (`assemble_pr_body`, `discover_issue_for_footer`)."
---

# PR Rewrite Command

`erk pr rewrite` replaces the old multi-step workflow (`gt squash` + `erk pr summarize` + push) with a single command that handles the full cycle.

## 6-Phase Pipeline

<!-- Source: src/erk/cli/commands/pr/rewrite_cmd.py, _execute_pr_rewrite -->

The command executes six phases sequentially:

1. **Validate** — Checks Claude CLI availability, current branch, and that a PR exists
2. **Squash** — Idempotent squash via `execute_squash()` (works whether 1 or N commits)
3. **Extract diff** — Gets the diff between current branch and parent via `execute_diff_extraction()`
4. **Generate AI title/body** — Uses `CommitMessageGenerator` with optional plan context from linked erk-plan issue
5. **Amend commit** — Rewrites the local commit with the AI-generated message
6. **Push and update PR** — Force-pushes via `branch_manager.submit_branch()`, updates PR title/body on GitHub

## Key Behaviors

**Idempotent squash**: Uses `execute_squash()` which works correctly whether the branch has 1 commit or N commits. Safe to run repeatedly.

**Graphite retracking**: After amending, the command retracks the branch via `ctx.graphite_branch_ops.retrack_branch()` to fix tracking divergence caused by the amend.

**PR body composition**: Uses shared `assemble_pr_body()` from `shared.py` for consistent body format including plan details section and footer with closing reference.

**Learn plan label handling**: Detects learn plan origin via `is_learn_plan()` and adds `ERK_SKIP_LEARN_LABEL` to skip redundant learn processing.

**Issue discovery**: Uses shared `discover_issue_for_footer()` for two-step issue discovery (`.impl/issue.json` primary, existing PR body fallback).

## Flags

- `--debug` — Shows diagnostic output from squash and diff extraction phases

## Usage

```bash
# Rewrite current PR with AI-generated message
erk pr rewrite

# Show debug output
erk pr rewrite --debug
```

## Related Topics

- [PR Body Assembly](../architecture/pr-body-assembly.md) — Shared utilities used by this command
- [PR Submit Pipeline Architecture](pr-submit-pipeline.md) — The submit pipeline that shares utilities with rewrite
