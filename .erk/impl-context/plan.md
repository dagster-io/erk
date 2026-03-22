# Plan: `erk objective execute` — Full Objective Execution Loop

## Context

The `erk exec objective-execute-plan` command currently only shows a dry-run preview of which nodes would be dispatched next. The user wants a fully automated execution loop that processes objective nodes sequentially: dispatching one-shot workflows, waiting for CI, handling reviews, and landing PRs — all capped by a `--count` parameter.

## Approach

Create a new CLI command `erk objective execute` that orchestrates the full lifecycle for each node. The command dispatches one-shot workflows (remote, via GitHub API), then polls for completion of each phase before moving to the next node.

Keep the existing `erk exec objective-execute-plan` as-is (useful as a dry-run preview building block).

## Command Interface

```
erk objective execute <issue_ref> --count N [--model <model>] [--poll-interval <seconds>] [--max-address-rounds <N>] [--ref <branch>] [--ref-current] [--dry-run]
```

**Defaults:**
- `--poll-interval`: 30 seconds
- `--max-address-rounds`: 3

## Per-Node Execution Loop

```
For each node (up to --count):
  1. Re-fetch objective → get next pending unblocked node
     (Re-fetches each iteration because landing updates the roadmap)
  2. Dispatch one-shot workflow (reuse dispatch_one_shot_remote)
     → returns pr_number, run_id
  3. Mark node as "planning" in objective roadmap
  4. Poll workflow run until status == "completed"
     - If conclusion != "success" → abort with error
  5. Wait for CI checks to pass
     - Initial grace period (60s) for checks to start
     - Poll get_pr_check_runs() until empty (no failing checks)
     - Timeout after 30 minutes → abort with error
  6. Check for unresolved review threads
     - Poll get_pr_review_threads(include_resolved=False)
     - If unresolved threads exist:
       a. Dispatch pr-address workflow
       b. Wait for pr-address workflow to complete
       c. Go back to step 5 (CI + reviews again)
       d. Max --max-address-rounds iterations
  7. Land the PR (merge via gateway)
  8. Update objective node to "done" (run_objective_update_after_land)
  9. Output: "Node X.Y complete! (N/count)"
```

On abort: report which node failed, at which phase, and exit. User can re-run — the loop picks up the next pending node.

## Files to Create/Modify

### New: `src/erk/cli/commands/objective/execute_cmd.py`

Main command file. Structure:

```python
# Polling helpers (private functions)
def _wait_for_workflow(github, repo_root, run_id, *, poll_interval) -> WorkflowRun
def _wait_for_ci(github, repo_root, pr_number, *, poll_interval, timeout) -> None
def _has_unresolved_threads(github, repo_root, pr_number) -> bool
def _address_and_wait(remote, github, repo_root, ...) -> str  # returns run_id

# Main command
@click.command("execute")
def execute_objective(ctx, issue_ref, count, model, poll_interval, ...) -> None
```

**Reused functions/modules:**
- `dispatch_one_shot_remote()` from `src/erk/cli/commands/one_shot_remote_dispatch.py`
- `_dispatch_pr_address()` from `src/erk/cli/commands/launch_cmd.py` (or extract the dispatch logic)
- `_resolve_next()` from `src/erk/cli/commands/objective/plan_cmd.py`
- `_update_objective_node()` from `src/erk/cli/commands/objective/plan_cmd.py`
- `run_objective_update_after_land()` from `src/erk/cli/commands/objective_helpers.py`
- `validate_objective()` from `src/erk/cli/commands/objective/check/validation.py`

**Gateway methods used:**
- `RemoteGitHub.dispatch_workflow()` — dispatch one-shot and pr-address
- `LocalGitHub.get_workflow_run(repo_root, run_id)` — poll workflow status
- `LocalGitHub.get_pr_check_runs(repo_root, pr_number)` — check CI (returns failing checks only; empty = pass)
- `LocalGitHub.get_pr_review_threads(repo_root, pr_number)` — check unresolved threads
- `LocalGitHub.merge_pr(repo_root, pr_number, squash=True, verbose=False)` — land PR

### Modify: `src/erk/cli/commands/objective/__init__.py`

Add `execute_objective` to the group:
```python
from erk.cli.commands.objective.execute_cmd import execute_objective
register_with_aliases(objective_group, execute_objective)
```

### New: `tests/unit/cli/commands/objective/test_execute_cmd.py`

Unit tests using fake gateways:
- Happy path: single node dispatched, CI passes, no reviews, landed
- Multi-node: 2 nodes processed sequentially
- Review addressing: unresolved threads trigger pr-address dispatch
- Max address rounds exceeded → error
- One-shot workflow failure → abort
- CI timeout → abort
- Dry-run mode → preview without dispatch
- All nodes already done → exits cleanly

## Key Design Decisions

1. **Re-fetch objective each iteration** — After landing a PR, the roadmap is updated. Re-fetching ensures we see the latest state and pick the correct next node.

2. **CI check detection** — `get_pr_check_runs()` returns failing checks. Empty list = all pass. A 60-second grace period after workflow completion handles the race where checks haven't started yet.

3. **Abort on failure** — If any step fails, abort the entire loop. User can re-run; the loop picks up where it left off (next pending node). No `--continue-on-error` for MVP.

4. **Separate from exec script** — The exec script remains a dry-run preview tool. This new CLI command is the orchestrator.

## Verification

1. Run `erk objective execute --help` to verify CLI registration
2. Run unit tests: `pytest tests/unit/cli/commands/objective/test_execute_cmd.py -v`
3. Run `erk objective execute <objective> --count 1 --dry-run` to verify dry-run preview
4. Run type checker against new files
5. End-to-end: `erk objective execute <objective> --count 1` against a real objective with pending nodes
