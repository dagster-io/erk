---
title: Consolidate Learn Plans Workflow
read_when:
  - "working with consolidate-learn-plans workflow"
  - "modifying the learn plan consolidation pipeline"
  - "adding new dispatch-based workflows via RemoteGitHub"
tripwires:
  - action: "dispatching consolidate-learn-plans via gh CLI"
    warning: "Use dispatch_consolidate_learn_plans() which uses RemoteGitHub REST API. It handles branch creation, PR creation, and workflow dispatch atomically."
---

# Consolidate Learn Plans Workflow

Automated pipeline that consolidates multiple open `erk-learn` plans into a single documentation update PR.

## Components

### Slash Commands

| Command                             | Mode        | Purpose                                               |
| ----------------------------------- | ----------- | ----------------------------------------------------- |
| `/erk:consolidate-learn-plans`      | Interactive | User-facing — queries plans, consolidates, implements |
| `/erk:consolidate-learn-plans-plan` | CI          | Autonomous — used by the GitHub Actions workflow      |

### Dispatch Module

`src/erk/cli/commands/consolidate_learn_plans_dispatch.py`

Handles the remote dispatch sequence entirely via GitHub REST API:

1. Authenticates via `RemoteGitHub`
2. Generates timestamped branch name: `consolidate-learn-plans-{MM-DD-HHMM}`
3. Creates branch from trunk SHA via `remote.create_ref()`
4. Commits static prompt file to `.erk/impl-context/prompt.md`
5. Creates draft PR with plan-header metadata and `erk-pr`, `erk-plan`, `erk-learn` labels
6. Dispatches `consolidate-learn-plans.yml` workflow
7. Posts queued event comment on the PR

Returns `ConsolidateLearnPlansDispatchResult(pr_number, run_id, branch_name)`.

### GitHub Actions Workflow

`.github/workflows/consolidate-learn-plans.yml`

Multi-job pipeline:

- **Inputs**: `branch_name`, `pr_number`, `submitted_by`, `distinct_id`, `model_name`
- **Concurrency**: Grouped by branch name, cancels in-progress runs
- **Permissions**: `contents: write`, `pull-requests: write`, `issues: write`
- **Timeout**: 45 minutes

### Launch Integration

`src/erk/cli/commands/launch_cmd.py:585-593`

The `consolidate-learn-plans` workflow is registered in `WORKFLOW_COMMAND_MAP` and dispatched via the unified launch handler. It delegates to `dispatch_consolidate_learn_plans()` from the dispatch module.

### Constants

`src/erk/cli/constants.py`:

```python
CONSOLIDATE_LEARN_PLANS_WORKFLOW_NAME = "consolidate-learn-plans.yml"
```

Registered in `WORKFLOW_COMMAND_MAP` as `"consolidate-learn-plans"`.

## Usage

```bash
# Interactive: user triggers consolidation
erk launch consolidate-learn-plans

# With specific model
erk launch consolidate-learn-plans --model claude-opus-4-6

# Remote: specify target repo
erk launch consolidate-learn-plans --repo owner/repo
```

## Related Documentation

- [Unified Dispatch Pattern](../architecture/unified-dispatch-pattern.md) — how launch_cmd.py routes to this handler
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — lifecycle stage management
