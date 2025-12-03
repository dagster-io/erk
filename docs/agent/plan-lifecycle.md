---
title: Plan Lifecycle
read_when:
  - "creating a plan"
  - "closing a plan"
  - "understanding plan states"
---

# Plan Lifecycle

Complete documentation for the erk plan lifecycle from creation through merge, using GitHub's native branch-to-issue linking.

## Table of Contents

- [Executive Summary](#executive-summary)
- [Phase 1: Plan Creation](#phase-1-plan-creation)
- [Phase 2: Plan Submission](#phase-2-plan-submission)
- [Phase 3: Workflow Dispatch](#phase-3-workflow-dispatch)
- [Phase 4: Implementation](#phase-4-implementation)
- [Phase 5: PR Finalization & Merge](#phase-5-pr-finalization--merge)
- [State Linking Mechanisms](#state-linking-mechanisms)
- [Metadata Block Reference](#metadata-block-reference)
- [Quick State Reconstruction](#quick-state-reconstruction)

---

## Executive Summary

The erk plan lifecycle manages implementation plans from creation through automated execution and PR merge, using GitHub's native branch-to-issue linking via `gh issue develop`.

### Lifecycle Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Create    │────▶│   Submit    │────▶│  Dispatch   │────▶│  Implement  │────▶│    Merge    │
│    Plan     │     │    Plan     │     │  Workflow   │     │    Plan     │     │     PR      │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                  │                   │                   │                   │
       ▼                  ▼                   ▼                   ▼                   ▼
 GitHub Issue       gh issue develop      GitHub Actions      Code Changes        Issue Closed
 with erk-plan      creates linked        finds existing      committed           via PR merge
 label              branch + PR           PR and executes     and pushed
```

### Key File Locations at a Glance

| Location               | Purpose                                           |
| ---------------------- | ------------------------------------------------- |
| `~/.claude/plans/*.md` | Local plan storage (sorted by modification time)  |
| `.impl/plan.md`        | Immutable plan in worktree (local implementation) |
| `.impl/progress.md`    | Mutable progress tracking                         |
| `.impl/issue.json`     | GitHub issue reference                            |
| `.impl/run-info.json`  | GitHub Actions run reference (remote only)        |
| `.worker-impl/`        | Remote implementation folder (GitHub Actions)     |

### Which Phase Am I In?

| Observable State                        | Current Phase                |
| --------------------------------------- | ---------------------------- |
| Issue has `erk-plan` label, no comments | Phase 1: Created             |
| Issue has `submission-queued` comment   | Phase 2: Submitted           |
| Issue has `workflow-started` comment    | Phase 3: Dispatched          |
| PR is draft, workflow running           | Phase 4: Implementing        |
| PR is ready for review                  | Phase 5: Complete            |
| Issue is CLOSED                         | Merged (PR closed the issue) |

---

## Phase 1: Plan Creation

Plans can be created through two paths: interactive (via Claude) or CLI (direct).

### Interactive Path: `/erk:craft-plan`

The interactive path uses Claude's plan mode for guided plan creation:

```bash
/erk:craft-plan
```

This workflow:

1. Enters Claude plan mode with structured prompts
2. Guides plan creation with context extraction
3. Saves plan to `~/.claude/plans/*.md` (local backup)
4. Creates GitHub Issue with `erk-plan` label

### CLI Path: `erk plan create --file <path>`

Direct plan creation from a file:

```bash
erk plan create --file my-plan.md
```

This creates a GitHub Issue directly from the plan file.

### Plan Storage: Schema v2

Plans are stored in GitHub Issues using Schema v2:

- **Issue body**: Contains `plan-header` metadata block
- **First comment**: Contains `plan-body` with full plan content in collapsible details

**Issue body structure:**

````markdown
# Plan: [Title]

<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml
created_at: 2025-01-15T10:30:00Z
created_by: username
last_dispatched_at: null
last_dispatched_run_id: null
last_local_impl_at: null
```
````

</details>
<!-- /erk:metadata-block:plan-header -->
```

**First comment structure:**

```markdown
<!-- erk:metadata-block:plan-body -->
<details>
<summary><code>plan-body</code></summary>

[Full plan content here]

</details>
<!-- /erk:metadata-block:plan-body -->
```

### The `erk-plan` Label

The `erk-plan` label marks issues as implementation plans:

- **Auto-created** if it doesn't exist (green, #0E8A16)
- **Required** for submission and implementation
- **Validated** before workflow dispatch

---

## Phase 2: Plan Submission

Submission prepares the plan for remote execution via `erk submit <issue_number>`.

**Key responsibility**: `erk submit` is the **source of truth** for branch and PR creation. The workflow dispatch (Phase 3) expects these to already exist.

### Pre-Submission Validation

Before submission, the command validates:

1. **Label check**: Issue must have `erk-plan` label
2. **State check**: Issue must be OPEN (not closed)
3. **Clean working directory**: No uncommitted changes

### Branch Creation via `gh issue develop`

Branches are created using GitHub's native `gh issue develop` command:

```bash
gh issue develop <issue_number> --base <trunk_branch> --name <branch_name>
```

This creates a branch linked to the issue that appears in the GitHub issue sidebar under "Development", providing automatic tracking without custom metadata.

**Branch naming**: Erk computes the branch name explicitly using `sanitize_worktree_name()` with a timestamp suffix, then passes it via `--name` flag. This ensures branch names match worktree naming conventions (31-char max + `-MM-DD-HHMM` suffix).

**Example**: Issue #123 "Add user authentication" → `123-add-user-authentic-11-30-1430`

**Reusing existing branches**: If a branch already exists for the issue, `gh issue develop --list` is used to discover it rather than creating a duplicate.

### `.worker-impl/` Folder Creation

The submit command creates the `.worker-impl/` folder structure:

```
.worker-impl/
├── plan.md         # Full plan content from issue
├── progress.md     # Initial progress tracking (all unchecked)
├── issue.json      # GitHub issue reference
└── README.md       # Documentation for the folder
```

**`issue.json` structure:**

```json
{
  "issue_number": 123,
  "issue_url": "https://github.com/owner/repo/issues/123",
  "created_at": "2025-01-15T10:30:00Z",
  "synced_at": "2025-01-15T10:30:00Z"
}
```

### Draft PR Creation

A draft PR is created locally (for correct commit attribution):

- **Title**: Issue title with "Plan: " prefix stripped
- **Body**: Includes checkout instructions and metadata
- **State**: Draft (marked ready after implementation)

**Note**: GitHub automatically links the PR to its issue via the native branch linking created by `gh issue develop`. No explicit "Closes #N" keyword is needed.

### `distinct_id` Generation

A 6-character base36 identifier is generated for workflow run discovery:

- Used in workflow `run-name` for matching
- Enables polling to find the specific run
- Format: `{issue_number}:{distinct_id}` in run display title

### Metadata Update

After submission, the issue receives a `submission-queued` comment with metadata:

```yaml
schema: submission-queued
queued_at: 2025-01-15T10:30:00Z
submitted_by: username
issue_number: 123
validation_results:
  issue_is_open: true
  has_erk_plan_label: true
expected_workflow: dispatch-erk-queue-git
```

---

## Phase 3: Workflow Dispatch

The `dispatch-erk-queue-git.yml` workflow handles remote implementation.

### Workflow Inputs

| Input          | Description                          |
| -------------- | ------------------------------------ |
| `issue_number` | GitHub issue number to implement     |
| `submitted_by` | GitHub username of submitter         |
| `distinct_id`  | 6-char base36 for run discovery      |
| `issue_title`  | Issue title for workflow run display |

### Concurrency Control

```yaml
concurrency:
  group: implement-issue-${{ github.event.inputs.issue_number }}
  cancel-in-progress: true
```

This ensures only one implementation runs per issue at a time.

### Workflow Phases

#### Phase 1: Checkout & Setup

- Checkout repository with full history
- Install tools: `uv`, `erk`, `dot-agent-kit`, `claude`, `prettier`
- Configure git with submitter identity
- Detect trunk branch (main or master)

#### Phase 2: Find PR & Checkout Branch

- Find linked branch via `gh issue develop --list <issue_number>` (native GitHub linking)
- Find existing PR via `gh pr list --head <branch_name>` (by branch, not body search)
- Checkout the implementation branch
- Update `.worker-impl/` with fresh plan content (for reruns)

#### Phase 3: Use Existing PR

- Use existing PR (created by `erk submit`)
- Post `workflow-started` comment to issue
- Update issue body with `last_dispatched_run_id`

#### Phase 4: Implementation

- Copy `.worker-impl/` to `.impl/` (Claude reads `.impl/`)
- Create `.impl/run-info.json` with workflow run details
- Execute `/erk:plan-implement` with Claude

#### Phase 5: Submission

- Stage implementation changes (NOT `.worker-impl/` deletion)
- Run `/git:pr-push` to create proper commit message
- Clean up `.worker-impl/` in separate commit
- Mark PR ready for review
- Update PR body with implementation summary
- Trigger CI via empty commit

---

## Phase 4: Implementation

Implementation executes the plan, whether locally or via GitHub Actions.

### `.worker-impl/` vs `.impl/`

| Folder          | Purpose                                      | Git Status                       |
| --------------- | -------------------------------------------- | -------------------------------- |
| `.worker-impl/` | Remote implementation (GitHub Actions)       | Committed, then deleted          |
| `.impl/`        | Local implementation + Claude's working copy | In `.gitignore`, never committed |

In GitHub Actions, `.worker-impl/` is copied to `.impl/` before Claude runs.

### `.impl/run-info.json`

Created in GitHub Actions to track the workflow run:

```json
{
  "run_id": "1234567890",
  "run_url": "https://github.com/owner/repo/actions/runs/1234567890"
}
```

### `/erk:plan-implement` Command

The implementation command:

1. Validates `.impl/` exists with `plan.md` and `progress.md`
2. Creates TodoWrite entries for tracking
3. Posts start comment to GitHub issue (if linked)
4. Executes each phase sequentially
5. Updates `progress.md` as steps complete
6. Runs CI validation
7. Cleans up artifacts

### Progress Tracking

Progress is tracked in `.impl/progress.md`:

```markdown
---
completed_steps: 3
total_steps: 5
steps:
  - text: "1. First step"
    completed: true
  - text: "2. Second step"
    completed: true
  - text: "3. Third step"
    completed: true
  - text: "4. Fourth step"
    completed: false
  - text: "5. Fifth step"
    completed: false
---

# Progress Tracking

- [x] 1. First step
- [x] 2. Second step
- [x] 3. Third step
- [ ] 4. Fourth step
- [ ] 5. Fifth step
```

Use kit CLI commands to update progress:

```bash
dot-agent run erk mark-step 1        # Mark step 1 complete
dot-agent run erk mark-step 1 2 3    # Mark multiple steps
dot-agent run erk get-progress       # Show current progress
```

---

## Phase 5: PR Finalization & Merge

The final phase prepares the PR for review and merge.

### `/git:pr-push` Submission

The pure git submission flow:

1. Analyze staged changes
2. Generate AI commit message
3. Commit with proper attribution
4. Push to remote
5. Update PR body with summary

### `.worker-impl/` Cleanup

In GitHub Actions, `.worker-impl/` is removed in a separate commit:

```bash
git rm -rf .worker-impl/
git commit -m "Remove .worker-impl/ folder after implementation"
git push
```

This keeps the implementation commit clean.

### PR Ready for Review

```bash
gh pr ready "$BRANCH_NAME"
```

Marks the draft PR as ready for review.

### PR Body Update

The PR body is updated with:

1. Implementation summary (from commit message)
2. Standardized footer from `get-pr-body-footer`
3. Checkout instructions

### CI Trigger

An empty commit triggers push-event workflows:

```bash
git commit --allow-empty -m "Trigger CI workflows"
git push
```

This is needed because workflow dispatch doesn't trigger PR workflows.

### Auto-Close on Merge

GitHub automatically closes the linked issue when the PR is merged. This is enabled by the native branch-to-issue linking created via `gh issue develop`.

**No explicit "Closes #N" keyword is required** - GitHub tracks the relationship through its native branch linking feature, which appears in the issue sidebar under "Development".

---

## State Linking Mechanisms

Entities are connected through GitHub's native linking and deterministic metadata.

### Branch → Issue (Native GitHub Linking)

Branches are linked to issues via GitHub's native `gh issue develop`:

```bash
gh issue develop <issue_number> --base <trunk_branch> --name <branch_name>
```

This creates a branch that appears in the GitHub issue sidebar under "Development", providing automatic bidirectional linking maintained by GitHub.

To discover existing linked branches:

```bash
gh issue develop --list <issue_number>
```

### PR → Issue

PRs are linked to issues through GitHub's native branch linking:

- The branch was created with `gh issue develop`, linking it to the issue
- GitHub displays this link in the issue sidebar under "Development"
- GitHub automatically closes the issue when the PR merges
- No explicit "Closes #N" keyword is required

### Issue → Workflow Run

The `plan-header` metadata block contains:

```yaml
last_dispatched_run_id: "1234567890"
last_dispatched_at: 2025-01-15T10:30:00Z
```

Updated by `update-dispatch-info` kit CLI command.

### Workflow Run → Issue

The workflow receives `issue_number` as input:

```yaml
inputs:
  issue_number:
    description: "GitHub issue number to implement"
    required: true
```

Available throughout as `${{ inputs.issue_number }}`.

### Run Discovery

The `distinct_id` enables finding the specific workflow run:

1. **Generation**: 6-char base36 created at dispatch time
2. **Run name**: Set to `"{issue_number}:{distinct_id}"`
3. **Polling**: Match runs by `displayTitle` containing `:distinct_id`

---

## Metadata Block Reference

All metadata blocks use a consistent format:

````html
<!-- erk:metadata-block:{key} -->
<details>
  <summary><code>{key}</code></summary>

  ```yaml {structured_data} ```
</details>
<!-- /erk:metadata-block:{key} -->
````

### Block Types

| Block Key                   | Location            | Purpose                                         |
| --------------------------- | ------------------- | ----------------------------------------------- |
| `plan-header`               | Issue body          | Plan metadata (created_at, dispatched_at, etc.) |
| `plan-body`                 | Issue first comment | Full plan content in collapsible details        |
| `submission-queued`         | Issue comment       | Marks submission to queue                       |
| `workflow-started`          | Issue comment       | Links to specific workflow run                  |
| `erk-implementation-status` | Issue comment       | Progress updates during implementation          |
| `erk-worktree-creation`     | Issue comment       | Documents local worktree creation               |

### `plan-header` Schema

```yaml
created_at: 2025-01-15T10:30:00Z
created_by: username
last_dispatched_at: 2025-01-15T11:00:00Z # null if never dispatched
last_dispatched_run_id: "1234567890" # null if never dispatched
last_local_impl_at: 2025-01-15T12:00:00Z # null if never implemented locally
```

### `submission-queued` Schema

```yaml
schema: submission-queued
queued_at: 2025-01-15T10:30:00Z
submitted_by: username
issue_number: 123
validation_results:
  issue_is_open: true
  has_erk_plan_label: true
expected_workflow: dispatch-erk-queue-git
```

### `workflow-started` Schema

```yaml
schema: workflow-started
status: started
started_at: 2025-01-15T10:30:00Z
workflow_run_id: "1234567890"
workflow_run_url: https://github.com/owner/repo/actions/runs/1234567890
branch_name: 123-add-user-authentic-11-30-1430
issue_number: 123
```

### `erk-implementation-status` Schema

```yaml
status: in_progress # pending, in_progress, complete, failed
completed_steps: 3
total_steps: 5
timestamp: 2025-01-15T10:30:00Z
step_description: "Implementing feature X" # optional
```

### `erk-worktree-creation` Schema

```yaml
worktree_name: 123-add-user-authentic-11-30-1430
branch_name: 123-add-user-authentic-11-30-1430
timestamp: 2025-01-15T10:30:00Z
issue_number: 123 # optional
```

---

## Quick State Reconstruction

### From Issue Number

```bash
# Get issue details
gh issue view 123 --json title,body,comments,labels

# Find linked branch
gh issue develop --list 123

# Find associated PR (via branch, not body search)
BRANCH=$(gh issue develop --list 123 | head -1 | cut -f1)
gh pr list --head "$BRANCH"

# Find workflow runs
gh run list --workflow=dispatch-erk-queue-git.yml | grep "123:"
```

### From Branch Name

```bash
# Get branch info
git log origin/123-add-user-authentic-11-30-1430 --oneline -5

# Find PR
gh pr view 123-add-user-authentic-11-30-1430

# Check for .worker-impl/
git ls-tree origin/123-add-user-authentic-11-30-1430 | grep worker-impl
```

### From PR Number

```bash
# Get PR details
gh pr view 456 --json title,body,headRefName

# Get linked issues via GitHub's native linking
gh pr view 456 --json closingIssuesReferences -q '.closingIssuesReferences[].number'
```

### From Workflow Run

```bash
# Get run details
gh run view 1234567890

# Extract issue from run name (format: "123:abc123")
gh run view 1234567890 --json displayTitle -q '.displayTitle' | cut -d: -f1
```

---

## Related Documentation

- [Planning Workflow](planning-workflow.md) - `.impl/` folder structure and commands
- [Plan Enrichment](plan-enrichment.md) - Context preservation in plans
- [Kit CLI Commands](kit-cli-commands.md) - Available `dot-agent run erk` commands
- [Glossary](glossary.md) - Erk terminology definitions
