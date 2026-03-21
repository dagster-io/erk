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

<!-- Source: src/erk/cli/commands/consolidate_learn_plans_dispatch.py, dispatch_consolidate_learn_plans -->

See `dispatch_consolidate_learn_plans()` in `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`. The function accepts a `RemoteGitHub` gateway, owner/repo identifiers, optional model name, dry-run flag, optional ref override, and a time gateway. Returns `ConsolidateLearnPlansDispatchResult(pr_number, run_id, branch_name)` or `None` in dry-run mode.

## Branch Naming

Branch name format: `consolidate-learn-plans-{MM-DD-HHMM}`

<!-- Source: src/erk/cli/commands/consolidate_learn_plans_dispatch.py, dispatch_consolidate_learn_plans -->

See `dispatch_consolidate_learn_plans()` in `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`. The function generates branch names using `format_branch_timestamp_suffix()` from `erk_shared.naming` — no LLM-generated slug needed because the purpose is fixed. Example: `consolidate-learn-plans-03-20-1430`.

## Static Prompt

<!-- Source: src/erk/cli/commands/consolidate_learn_plans_dispatch.py, dispatch_consolidate_learn_plans -->

The prompt is hardcoded (not config-driven). See `dispatch_consolidate_learn_plans()` in `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`. The static prompt directs users to consolidate all open erk-learn PRs into a single documentation update and run the `/erk:system:consolidate-learn-plans-plan` command. The prompt content is committed to `.erk/impl-context/prompt.md` on the new branch via `remote.create_file_commit()`.

## Labels

<!-- Source: src/erk/cli/commands/consolidate_learn_plans_dispatch.py, dispatch_consolidate_learn_plans -->

Both labels (`erk-pr` and `erk-learn`) are applied to the created PR. See `dispatch_consolidate_learn_plans()` in `src/erk/cli/commands/consolidate_learn_plans_dispatch.py` for the label application logic.

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

<!-- Source: src/erk/cli/commands/consolidate_learn_plans_dispatch.py, CONSOLIDATE_LEARN_PLANS_WORKFLOW -->

See `CONSOLIDATE_LEARN_PLANS_WORKFLOW` in `src/erk/cli/commands/consolidate_learn_plans_dispatch.py`. The constant holds the workflow filename `"consolidate-learn-plans.yml"` and is used to dispatch the CI workflow.

## Related Documentation

- [Unified Dispatch Pattern](../architecture/unified-dispatch-pattern.md) — how `erk launch` routes to this handler
- [Planned PR Lifecycle](planned-pr-lifecycle.md) — full plan lifecycle
