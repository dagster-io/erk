# Consolidate code-reviews workflow into reusable workflow

## Context

Commit `4bccacb3c` deleted `.github/workflows/code-reviews.yml` and moved those jobs into `ci.yml` to get a `needs: [fix-formatting]` dependency. It also removed `code-reviews.yml` from `pyproject.toml` force-include.

However, `CodeReviewsSystemCapability` still tries to install `code-reviews.yml` into external repos (e.g. `internal`). The stale `.venv` wheel still has the old template, but:
1. The template is no longer in the erk source tree (so next wheel build won't include it)
2. The template's `uv tool install --from . --with ./packages/erk-shared erk` fails in non-erk repos where `--from .` resolves to the host package name (e.g. `internal`), not `erk`

Fix: make `code-reviews.yml` a reusable workflow (`workflow_call`) with a thin trigger file for external repos. Erk's `ci.yml` calls the reusable workflow with `needs: [fix-formatting]` for proper ordering.

## Plan

### 1. Create `.github/workflows/code-reviews.yml` as a reusable workflow

Based on git history (commit `2bbcbfc67`), but converted to `on: workflow_call` and with fixed erk install steps.

Key changes from the original:
- Trigger: `on: workflow_call` (not `pull_request`)
- Top-level `permissions: contents: read, pull-requests: write`
- Both install steps use the conditional pattern:
  ```yaml
  - name: Install erk
    run: |
      if [ -d "./packages/erk-shared" ]; then
        uv tool install --from . --with ./packages/erk-shared erk
      else
        uv sync --group dev
        echo "$GITHUB_WORKSPACE/.venv/bin" >> $GITHUB_PATH
      fi
  ```
- `discover` job keeps: local review marker check, CLAUDE_ENABLED/draft/plan-review conditions
- `review` job keeps: `needs: discover`, matrix strategy, Claude Code + erk install, run-review exec

### 2. Create `.github/workflows/code-reviews-trigger.yml` (thin trigger for external repos)

```yaml
name: code-reviews
on:
  pull_request:
    types: [opened, synchronize, ready_for_review]
jobs:
  code-reviews:
    uses: ./.github/workflows/code-reviews.yml
    secrets: inherit
```

This file is installed into external repos by the capability. The erk repo does NOT use this file (ci.yml calls code-reviews.yml directly).

### 3. Update `ci.yml`: replace inline jobs with reusable workflow call

Remove `discover-reviews` + `review` jobs (lines 480-598). Add:

```yaml
  code-reviews:
    needs: [check-submission, fix-formatting]
    if: >-
      vars.CLAUDE_ENABLED != 'false' &&
      github.event.pull_request.draft != true &&
      !contains(github.event.pull_request.labels.*.name, 'erk-plan-review') &&
      needs.check-submission.outputs.skip == 'false'
    uses: ./.github/workflows/code-reviews.yml
    secrets: inherit
```

This preserves the fix-formatting ordering in the erk repo.

### 4. Update `pyproject.toml` force-include

Add both workflow files (after line 88):

```toml
# Convention-based code reviews
".github/workflows/code-reviews.yml" = "erk/data/github/workflows/code-reviews.yml"
".github/workflows/code-reviews-trigger.yml" = "erk/data/github/workflows/code-reviews-trigger.yml"
```

### 5. Update `CodeReviewsSystemCapability` (`src/erk/capabilities/code_reviews_system.py`)

Add the trigger file to `_get_installable_items()`:

```python
InstallableItem(
    source_path="workflows/code-reviews-trigger.yml",
    target_path=".github/workflows/code-reviews-trigger.yml",
    item_type="file",
    display_name="code-reviews-trigger.yml",
),
```

Also add to `artifacts` and `managed_artifacts` properties.

## Files to modify

- `.github/workflows/code-reviews.yml` — **create** (reusable workflow from git history `2bbcbfc67`, with `workflow_call` trigger + fixed install)
- `.github/workflows/code-reviews-trigger.yml` — **create** (thin trigger for external repos)
- `.github/workflows/ci.yml` — replace `discover-reviews` + `review` jobs (lines 480-598) with `uses:` call
- `pyproject.toml` — add force-include entries for both workflow files
- `src/erk/capabilities/code_reviews_system.py` — add trigger file to installable items

## Verification

1. Run `make fast-ci` to ensure nothing breaks
2. Push branch and verify:
   - `code-reviews` workflow triggers via ci.yml's `uses:` call
   - `discover` and `review` jobs run within that workflow
   - No duplicate standalone `code-reviews` workflow run (since trigger file isn't in erk repo)
