---
title: Consolidate Learn Plans Workflow
read_when:
  - "working with consolidate-learn-plans dispatch"
  - "adding or modifying the consolidate-learn-plans workflow"
  - "understanding how learn plan consolidation branches are named"
  - "working with erk launch consolidate-learn-plans"
tripwires:
  - action: "changing the prompt for consolidate-learn-plans to be config-driven"
    warning: "The prompt is hardcoded (static). See consolidate_learn_plans_dispatch.py lines 123-126. The purpose is fixed; no LLM slug or config needed. See consolidate-learn-plans-workflow.md."
  - action: "adding a LLM-generated slug to the consolidate-learn-plans branch name"
    warning: "Branch name uses format_branch_timestamp_suffix() only — no LLM slug. Format: consolidate-learn-plans-{MM-DD-HHMM}. See consolidate-learn-plans-workflow.md."
---

# Consolidate Learn Plans Workflow

Dispatches a remote workflow to consolidate all open erk-learn PRs into a single documentation update.

## Entry Points

| Entry Point          | How                                                                   |
| -------------------- | --------------------------------------------------------------------- |
| Interactive skill    | `erk exec consolidate-learn-plans` via `/erk:consolidate-learn-plans` |
| `erk launch` command | `erk launch consolidate-learn-plans`                                  |
| CI workflow          | `.github/workflows/consolidate-learn-plans.yml` (workflow_dispatch)   |

## Dispatch Function

`dispatch_consolidate_learn_plans()` in `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`:

```python
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

Returns `ConsolidateLearnPlansDispatchResult(pr_number, run_id, branch_name)` or `None` in dry-run mode.

## Branch Naming

Branch name format: `consolidate-learn-plans-{MM-DD-HHMM}`

Uses `format_branch_timestamp_suffix()` from `erk_shared.naming` — no LLM-generated slug needed because the purpose is fixed. Example: `consolidate-learn-plans-03-20-1430`.

```python
BRANCH_PREFIX = "consolidate-learn-plans"

def _generate_branch_name(*, time_gateway: Time) -> str:
    timestamp = format_branch_timestamp_suffix(time_gateway.now())
    return f"{BRANCH_PREFIX}{timestamp}"
```

## Static Prompt

The prompt is hardcoded (not config-driven):

```python
prompt_content = (
    "Consolidate all open erk-learn PRs into a single documentation update.\n"
    "Run /erk:system:consolidate-learn-plans-plan to query, consolidate, and implement.\n"
)
```

Committed to `.erk/impl-context/prompt.md` on the new branch via `remote.create_file_commit()`.

## Labels

Both labels applied to the created PR:

```python
remote.add_labels(
    owner=owner,
    repo=repo,
    issue_number=pr_number,
    labels=("erk-pr", "erk-learn"),
)
```

## Dispatch Sequence

1. Get authenticated user via `remote.get_authenticated_user()`
2. Get trunk SHA via `remote.get_default_branch_sha()`
3. Create branch from trunk via `remote.create_ref()`
4. Commit static prompt to `.erk/impl-context/prompt.md` via `remote.create_file_commit()`
5. Create draft PR via `remote.create_pull_request()`
6. Add footer and update PR body
7. Add labels: `"erk-pr"` and `"erk-learn"`
8. Build workflow inputs: `branch_name`, `pr_number`, `submitted_by`, optional `model_name`
9. Dispatch `consolidate-learn-plans.yml` workflow via `remote.dispatch_workflow()`
10. Post queued event comment (best-effort, catches `HttpError`)

## Workflow File

`CONSOLIDATE_LEARN_PLANS_WORKFLOW = "consolidate-learn-plans.yml"`

The CI workflow:

- Runs Claude with `/erk:system:consolidate-learn-plans-plan`
- Checks `plan-result.json` for `has_plans`
- If no plans: closes the draft PR automatically
- If plans found: calls `plan-implement.yml` reusable workflow
- Post-implementation: optional CI fix and rebase-if-needed jobs

## Workflow Constant

```python
CONSOLIDATE_LEARN_PLANS_WORKFLOW = "consolidate-learn-plans.yml"
```

Located at top of `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`.

## Related Documentation

- [Unified Dispatch Pattern](../architecture/unified-dispatch-pattern.md) — how `erk launch` routes to this handler
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — full plan lifecycle
