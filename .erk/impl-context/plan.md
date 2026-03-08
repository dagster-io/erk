# Plan: `erk launch consolidate-learn-plans` — Autonomous Learn Plan Consolidation & Implementation

## Context

Learn plans (`erk-learn` label) accumulate as PRs land and `/erk:learn` extracts documentation opportunities. Currently, consolidating and implementing these plans requires manual orchestration via the interactive `/local:replan-learn-plans` skill, followed by manual dispatch, CI address, and rebase.

The goal: `erk launch consolidate-learn-plans` → a single GitHub Actions workflow autonomously consolidates all outstanding learn plans, implements the consolidated plan, creates a PR, does one round of CI feedback addressing, and handles rebase if needed. Fire and forget, end up with one PR containing all doc updates.

## Changes Overview

1. **Rename** `/local:replan-learn-plans` → `/erk:consolidate-learn-plans` (move from local to erk)
2. **New workflow** `consolidate-learn-plans.yml` — multi-job pipeline
3. **New skill** `/erk:consolidate-learn-plans-plan` — CI-only skill for consolidation phase
4. **New launch handler** — add `consolidate-learn-plans` to `erk launch` with branch+PR creation
5. **New dispatch module** — branch/PR creation + workflow dispatch logic

## New Files

### 1. `.claude/commands/erk/consolidate-learn-plans.md` (rename from local)

Move `.claude/commands/local/replan-learn-plans.md` → `.claude/commands/erk/consolidate-learn-plans.md`

Update the content to:
- Remove `local:` prefix references
- Keep the interactive flow (AskUserQuestion for confirmation) — this is the "run locally in Claude Code" version
- Update the invocation of `/erk:replan` (no changes to the underlying replan logic)

### 2. `.claude/commands/erk/consolidate-learn-plans-plan.md` — CI consolidation skill

Non-interactive CI-only skill that runs during the `consolidate` workflow job. This is the autonomous version of the interactive skill above.

Steps:
1. Query open `erk-learn` plans via `gh api repos/{owner}/{repo}/issues` REST endpoint
2. Filter out `erk-consolidated` plans
3. If zero plans: write sentinel `plan-result.json` (`plan_number: 0`, `has_plans: false`) and exit cleanly
4. Fetch plan bodies via `erk exec get-plan-info <N> --include-body`
5. Launch Explore agents to investigate codebase against each plan item
6. Write implementation-ready plan to `.erk/impl-context/plan.md` (concrete file create/edit steps for `docs/learned/`)
7. Save plan metadata via `erk exec plan-update`
8. Write `.erk/impl-context/plan-result.json` with `plan_number`, `title`, `has_plans: true`
9. Close original learn plans with cross-reference comments and `erk-consolidated` label

Key difference from `/erk:replan`: outputs an **implementation plan** (file operations), not a new plan PR.

### 3. `.github/workflows/consolidate-learn-plans.yml` — GitHub Actions workflow

Multi-job workflow with five phases:

```yaml
name: consolidate-learn-plans
run-name: "consolidate-learn-plans:#${{ inputs.pr_number }}:${{ inputs.distinct_id }}"

on:
  workflow_dispatch:
    inputs:
      branch_name: { required: true, type: string }
      pr_number: { required: true, type: string }
      submitted_by: { required: true, type: string }
      distinct_id: { required: true, type: string }
      model_name: { required: false, type: string, default: "claude-opus-4-6" }

concurrency:
  group: consolidate-learn-plans-${{ inputs.branch_name }}
  cancel-in-progress: true
```

**Jobs:**

```
consolidate (45min):
  → Setup + checkout branch
  → Claude runs /erk:consolidate-learn-plans-plan
  → Outputs: plan_id, plan_title, base_branch, has_plans
  → If no plans: outputs has_plans=false, workflow skips rest

close-empty-pr (5min):
  → needs: consolidate
  → if: has_plans == 'false'
  → Close the draft PR (auto-cleanup)

implement:
  → needs: consolidate
  → if: has_plans == 'true'
  → uses: ./.github/workflows/plan-implement.yml (reuse existing)
  → Passes plan_id, branch_name, pr_number, model_name, base_branch

ci-address (30min):
  → needs: [consolidate, implement]
  → if: has_plans == 'true' && implement succeeded
  → Checkout PR branch
  → Poll CI: gh pr checks $PR_NUMBER --watch --fail-level all (with timeout)
  → If CI failures: Claude runs /erk:pr-address --pr $PR_NUMBER
  → Push fixes

rebase-if-needed (15min):
  → needs: [consolidate, implement, ci-address]
  → if: has_plans == 'true' && implement succeeded && always()
  → Check mergeable status via gh api
  → If CONFLICTING: erk exec rebase-with-conflict-resolution
  → Force push rebased branch
```

### 4. `src/erk/cli/commands/consolidate_learn_plans_dispatch.py` — Dispatch logic

Follows `one_shot_remote_dispatch.py` pattern. Creates branch + draft PR + dispatches workflow, all via RemoteGitHub REST API.

```python
CONSOLIDATE_LEARN_PLANS_WORKFLOW = "consolidate-learn-plans.yml"

@dataclass(frozen=True)
class ConsolidateLearnPlansDispatchResult:
    pr_number: int
    run_id: str
    branch_name: str

def dispatch_consolidate_learn_plans(
    *,
    remote: RemoteGitHub,
    owner: str,
    repo: str,
    model: str | None,
    dry_run: bool,
    ref: str | None,
    time_gateway: Time,
) -> ConsolidateLearnPlansDispatchResult | None:
```

Key details:
- Branch name: `consolidate-learn-plans-{MM-DD-HHMM}` (no LLM slug, fixed prefix)
- PR title: `"Consolidate learn plans"`
- Labels: `erk-pr`, `erk-plan`, `erk-learn`
- Static prompt committed to `.erk/impl-context/prompt.md`
- No `--prompt` or `--slug` params needed (purpose is fixed)

### 5. Tests

- `tests/commands/test_consolidate_learn_plans_dispatch.py` — dispatch function tests using `FakeRemoteGitHub`
  - Happy path: branch creation, prompt commit, PR creation, labels, workflow dispatch
  - Dry-run: None return, no mutations
  - Branch naming format validation

## Modified Files

### 6. `src/erk/cli/commands/launch_cmd.py`

Add handler and routing:

```python
def _dispatch_consolidate_learn_plans(
    ctx: ErkContext,
    repo: RepoContext,
    *,
    model: str | None,
    ref: str | None,
) -> None:
    """Dispatch consolidate-learn-plans workflow with branch + PR creation."""
    # Uses RemoteGitHub to create branch, PR, and dispatch
    # (delegates to consolidate_learn_plans_dispatch module)
```

Add routing in the main `launch()` function:
```python
elif workflow_name == "consolidate-learn-plans":
    _dispatch_consolidate_learn_plans(ctx, repo, model=model, ref=ref)
```

Update the docstring to list `consolidate-learn-plans` as an available workflow.

### 7. `src/erk/cli/constants.py`

Add workflow constant and map entry:
```python
CONSOLIDATE_LEARN_PLANS_WORKFLOW_NAME = "consolidate-learn-plans.yml"

# In WORKFLOW_COMMAND_MAP:
"consolidate-learn-plans": CONSOLIDATE_LEARN_PLANS_WORKFLOW_NAME,
```

### 8. Delete `.claude/commands/local/replan-learn-plans.md`

Remove the old local skill (replaced by the erk-level skill).

## Key Design Decisions

1. **Reuse `plan-implement.yml` via `workflow_call`** for the implement phase — same proven pattern as `one-shot.yml`.

2. **Separate `close-empty-pr` job** — auto-closes the draft PR when no learn plans exist, keeping things clean.

3. **One round of CI address only** — prevents infinite loops. If CI still fails after one round, human reviews.

4. **Branch/PR creation in CLI dispatch** (not in the workflow) — user sees PR URL immediately, follows the one-shot pattern.

5. **Two separate skills**: `/erk:consolidate-learn-plans` (interactive, for local use) and `/erk:consolidate-learn-plans-plan` (autonomous, for CI). The interactive version preserves AskUserQuestion confirmations; the CI version runs without human interaction.

## Implementation Order

1. Constants (`constants.py`) — add workflow name + map entry
2. Dispatch logic (`consolidate_learn_plans_dispatch.py`) — core dispatch function
3. Launch handler (`launch_cmd.py`) — routing + handler function
4. Dispatch tests (`test_consolidate_learn_plans_dispatch.py`)
5. Rename skill (`local/replan-learn-plans.md` → `erk/consolidate-learn-plans.md`)
6. CI skill (`erk/consolidate-learn-plans-plan.md`)
7. Workflow (`consolidate-learn-plans.yml`)
8. Delete old local skill

## Critical Files to Reference During Implementation

- `src/erk/cli/commands/one_shot_remote_dispatch.py` — primary dispatch pattern (branch/PR creation via RemoteGitHub)
- `src/erk/cli/commands/one_shot.py` — Click command calling remote dispatch (for RemoteGitHub instantiation)
- `.github/workflows/one-shot.yml` — plan → implement workflow pattern
- `.github/workflows/pr-address.yml` — CI address pattern
- `.github/workflows/pr-rebase.yml` — rebase pattern
- `.github/actions/erk-remote-setup/action.yml` — CI setup action
- `.claude/commands/local/replan-learn-plans.md` — existing consolidation logic to port
- `.claude/commands/erk/replan.md` — underlying replan skill
- `src/erk/cli/commands/launch_cmd.py` — launch command routing
- `src/erk/cli/constants.py` — workflow constants and map

## Verification

1. **Unit tests**: `uv run pytest tests/commands/test_consolidate_learn_plans_dispatch.py`
2. **Dry-run**: `erk launch consolidate-learn-plans --model claude-sonnet-4-6` (should error without `--dry-run` flag or... actually `erk launch` doesn't have `--dry-run`. The handler should just work.)
3. **CI integration**: Run `erk launch consolidate-learn-plans` with open learn plans → verify full pipeline produces a PR
4. **No-plans edge case**: Run when no learn plans exist → verify PR is auto-closed
5. **CI pass**: Verify the implementation passes `make fast-ci`
