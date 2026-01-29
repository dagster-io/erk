---
title: PR Address Workflows
read_when:
  - "addressing PR review comments"
  - "choosing between local and remote PR addressing"
  - "understanding erk pr address-remote"
  - "understanding /erk:pr-address command"
---

# PR Address Workflows

Erk provides two workflows for addressing PR review comments using Claude:

1. **Local** (`/erk:pr-address`) - Claude Code slash command, runs in your terminal
2. **Remote** (`erk pr address-remote`) - GitHub Actions workflow, runs in CI

## Decision Matrix

| Factor                       | Local                        | Remote                          |
| ---------------------------- | ---------------------------- | ------------------------------- |
| **Branch checkout**          | Required (must be on branch) | Not required                    |
| **Interactive confirmation** | Yes (via Claude Code)        | No                              |
| **Error recovery**           | Immediate (fix and retry)    | Check workflow logs             |
| **Plan metadata tracking**   | Manual                       | Automatic for P{issue} branches |
| **Best for**                 | Active development           | Queued/async work               |

## Local Workflow: /erk:pr-address

The `/erk:pr-address` slash command addresses review comments on the current branch.

### Usage

```bash
# Must be on the PR branch
erk br co my-feature
/erk:pr-address
```

### What it does

1. Fetches unresolved review comments from GitHub
2. Presents each comment to Claude for addressing
3. Claude makes code changes to address the feedback
4. You review and commit the changes

### When to use

- You're actively working on the branch
- You want interactive control over changes
- You want to review changes before committing

### Plan Review Mode

When the PR has the `plan-review` label, `/erk:pr-address` automatically switches to **Plan Review Mode**. This mode is designed for addressing feedback on plan-only PRs (no code changes).

#### How it's triggered

The `plan-review` label is applied automatically by `erk exec plan-create-review-pr`. The `/erk:pr-address` command detects this label in Phase 0 and switches modes.

See [Phase 0 Detection Pattern](../architecture/phase-zero-detection-pattern.md) for the detection mechanism.

#### What's different in Plan Review Mode

| Aspect                | Code Review Mode       | Plan Review Mode                                |
| --------------------- | ---------------------- | ----------------------------------------------- |
| **File modified**     | Source code files      | `PLAN-REVIEW-{issue}.md`                        |
| **Sync mechanism**    | Git push only          | Git push + `erk exec plan-update-from-feedback` |
| **Thread resolution** | Generic acknowledgment | Plan-specific messages                          |
| **Target audience**   | Code reviewers         | Plan reviewers                                  |

#### Plan Review Workflow

1. **Fetch feedback**: Get unresolved review comments from PR
2. **Edit plan file**: Make changes to `PLAN-REVIEW-{issue}.md` based on feedback
3. **Commit changes**: Commit the edited plan file
4. **Sync to GitHub issue**: Run `erk exec plan-update-from-feedback` to sync changes back to the issue
5. **Resolve threads**: Mark review threads as resolved with plan-specific messages

See [Plan File Sync Pattern](../architecture/plan-file-sync-pattern.md) for sync mechanics.

#### Why separate sync is needed

Plan review PRs maintain plan content in two locations:

- **PR branch**: `PLAN-REVIEW-{issue}.md` file (for version control)
- **GitHub issue**: Plan-body comment (for structured review)

The git push updates the PR, but doesn't update the issue. The explicit sync command ensures reviewers see changes in both locations.

#### When Plan Review Mode is used

- User runs `erk exec plan-create-review-pr` to create a review PR
- PR gets `plan-review` label automatically
- User runs `/erk:pr-address` on that PR branch
- Mode is detected automatically, no manual selection needed

See [PR-Based Plan Review Workflow](../planning/pr-review-workflow.md) for the complete plan review process.

## Remote Workflow: erk pr address-remote

The `erk pr address-remote` command triggers a GitHub Actions workflow to address comments without local checkout.

### Usage

```bash
# From any directory in the repo
erk pr address-remote 123

# With a specific model
erk pr address-remote 123 --model claude-opus-4
```

### What it does

1. Triggers `pr-address.yml` GitHub Actions workflow
2. Workflow checks out the PR branch
3. Runs `/erk:pr-address` in CI
4. Pushes any changes
5. Posts a summary comment on the PR

### Plan Dispatch Metadata Tracking

When the branch name follows the `P{issue_number}-*` pattern (e.g., `P5819-add-feature`), the command automatically updates the plan issue with dispatch metadata:

- `last_dispatch_run_id` - The workflow run ID
- `last_dispatch_node_id` - The workflow run node ID (for GraphQL)
- `last_dispatched_at` - ISO timestamp

This enables tracking which workflow runs are associated with which plans.

### Requirements

- PR must exist and be OPEN
- GitHub Actions secrets configured:
  - `ERK_QUEUE_GH_PAT` - PAT with `repo` scope
  - `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY`

### When to use

- You don't want to switch branches locally
- You're processing multiple PRs in a queue
- You want async/background processing

## Summary Comment

After the remote workflow completes, it posts (or updates) a summary comment on the PR with:

- Model used
- Job status (success/failure)
- Link to workflow run
- Summary of changes made

The comment uses the marker `<!-- erk:pr-address-run -->` to find and update existing comments.

## Related Topics

- [PR Sync Workflow](pr-sync-workflow.md) - Syncing PR title/body from commits
- [PR Submit Phases](../pr-operations/pr-submit-phases.md) - PR creation workflow
