# Plan: Add Workflow Run Backlink to Plans Created from GitHub Actions

## Context

When plans are created from GitHub Actions workflow runs (e.g., learn plans from `learn-dispatch.yml`), there should be a backlink to the workflow run that created them.

## Approach

**Explicit environment variable** - the workflow exports `WORKFLOW_RUN_URL`, and the `/erk:learn` command passes it to `plan-save-to-issue`. Same pattern used in `erk-impl.yml`.

## Files to Modify

### 1. Schema: `packages/erk-shared/src/erk_shared/github/metadata/schemas.py`

Add to `PlanHeaderFieldName` literal type:
- `"created_from_workflow_run_url"`

Add constant and validation for the optional string field.

### 2. Plan header: `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py`

Add `created_from_workflow_run_url: str | None` parameter to `create_plan_header_block()` and `format_plan_header_body()`.

### 3. Plan issues: `packages/erk-shared/src/erk_shared/github/plan_issues.py`

Add `created_from_workflow_run_url: str | None` parameter to `create_plan_issue()`.

### 4. CLI: `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py`

Add `--created-from-workflow-run-url` CLI option.

### 5. Learn command: `.claude/commands/erk/learn.md`

Update Step 6 to pass `--created-from-workflow-run-url "$WORKFLOW_RUN_URL"` if the env var is set.

### 6. Workflow: `.github/workflows/learn-dispatch.yml`

Add to the "Run learn workflow" step:
```yaml
env:
  WORKFLOW_RUN_URL: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
```

## Verification

1. Run `make fast-ci`
2. Test by running learn-dispatch workflow and verifying the created plan issue has the backlink in its metadata