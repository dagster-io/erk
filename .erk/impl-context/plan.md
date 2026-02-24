# Fix: pr-address workflow not showing run-id in TUI dashboard

## Context

PR #8028 was launched via the TUI's "address remote" action (`erk launch pr-address --pr 8028 --no-wait`, fire-and-forget dispatch). The workflow ran and completed (18/18 checks, `remote-imp: 1h ago`), but the `run-id` and `run` columns show "-" in the dashboard.

**Root cause:** The fire-and-forget dispatch path has a two-phase metadata write:

1. **Local CLI** writes a pending sentinel (`last_dispatched_run_id: null, last_dispatched_node_id: null`) via `maybe_write_pending_dispatch_metadata()`
2. **Workflow step 3** ("Write dispatch metadata to plan") is supposed to overwrite with real values, but has `continue-on-error: true` and is silently failing
3. **Workflow step 9** ("Update plan header with remote impl info") succeeds and writes `last_remote_impl_*` fields, but does NOT write `last_dispatched_*` fields

The dashboard reads `last_dispatched_node_id` from the PR body to look up workflow runs. Since it's still `null` (pending sentinel never overwritten), the run columns show "-".

**Why other PRs work:** PRs dispatched via `plan-submit`/`plan-implement` use the polling variant (`trigger_workflow()`), which writes dispatch metadata LOCALLY via `maybe_update_plan_dispatch_metadata()` before the workflow starts.

## Fix

### 1. `.github/workflows/pr-address.yml` (lines 150-165)

Add dispatch metadata fields to the "Update plan header with remote impl info" step. This step already runs `if: always()` and succeeds (confirmed by `remote-imp: 1h ago` in dashboard). Add `REPO` env var and `NODE_ID` lookup, then include `last_dispatched_run_id`, `last_dispatched_node_id`, `last_dispatched_at` in the `update-plan-header` call:

```yaml
- name: Update plan header with remote impl info
  if: always() && steps.plan_info.outputs.plan_id
  continue-on-error: true
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
    PLAN_ID: ${{ steps.plan_info.outputs.plan_id }}
    RUN_ID: ${{ github.run_id }}
    SESSION_ID: ${{ steps.session.outputs.session_id }}
    BRANCH_NAME: ${{ steps.plan_info.outputs.branch_name }}
    REPO: ${{ github.repository }}
  run: |
    NODE_ID=$(gh api "/repos/$REPO/actions/runs/$RUN_ID" --jq '.node_id')
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
    erk exec update-plan-header "$PLAN_ID" \
      "last_remote_impl_at=$TIMESTAMP" \
      "last_remote_impl_run_id=$RUN_ID" \
      "last_remote_impl_session_id=$SESSION_ID" \
      "branch_name=$BRANCH_NAME" \
      "last_dispatched_run_id=$RUN_ID" \
      "last_dispatched_node_id=$NODE_ID" \
      "last_dispatched_at=$TIMESTAMP"
```

### 2. `.github/workflows/pr-fix-conflicts.yml`

This workflow has the same early "Write dispatch metadata" step but NO final "Update plan header" step. Add one at the end, after the "Post status comment to PR" step:

```yaml
- name: Update plan header with dispatch metadata
  if: always() && inputs.plan_number != ''
  continue-on-error: true
  env:
    GH_TOKEN: ${{ secrets.ERK_QUEUE_GH_PAT }}
    PLAN_NUMBER: ${{ inputs.plan_number }}
    RUN_ID: ${{ github.run_id }}
    REPO: ${{ github.repository }}
  run: |
    NODE_ID=$(gh api "/repos/$REPO/actions/runs/$RUN_ID" --jq '.node_id')
    TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%S+00:00")
    erk exec update-plan-header "$PLAN_NUMBER" \
      "last_dispatched_run_id=$RUN_ID" \
      "last_dispatched_node_id=$NODE_ID" \
      "last_dispatched_at=$TIMESTAMP"
```

### Key design decisions

- **Keep step 3 ("Write dispatch metadata") as-is:** It provides early visibility (run link while workflow is still running). It's a best-effort step that may fail.
- **Add dispatch metadata to the final step as belt-and-suspenders:** Guarantees the metadata is written by workflow completion.
- **Single `update-plan-header` call:** The merge semantics of `update_metadata()` make it safe to include all fields in one call.

## Verification

1. Check existing tests: `pytest tests/unit/cli/commands/launch/ tests/unit/cli/commands/pr/test_metadata_helpers.py`
2. After deploying, trigger `erk launch pr-address --pr <pr> --no-wait` and verify run-id appears in dashboard after workflow completes
3. Verify `erk launch pr-fix-conflicts --pr <pr> --no-wait` also shows run-id
