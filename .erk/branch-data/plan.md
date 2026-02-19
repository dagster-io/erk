# Replace Gist-Based Learn Materials with Branch-Committed Files under `.erk/pr-files/`

## Context

The learn pipeline currently uploads preprocessed session materials to GitHub gists for transfer from local machines to CI. Secret gists lack real access control — anyone with the URL can read the content, which may include session data with file paths and API patterns. This plan replaces gist-based learn material transfer with files committed directly to the plan's draft PR branch under `.erk/pr-files/`, providing proper repo-scoped access control.

**Scope**: Draft PR backend only. The github (issues) backend continues using gists unchanged.

**Key invariant**: `.erk/pr-files/` exists only during the pre-implementation phase. It is deleted after implementation completes. Landing errors if it still exists.

---

## Phase 1: Rename `.erk/plan/` to `.erk/pr-files/`

Two files reference the `.erk/plan/` path:

### `src/erk/cli/commands/exec/scripts/plan_save.py` (lines 148-152)

In `_save_as_draft_pr()`:
- Line 148: `repo_root / ".erk" / "plan"` → `repo_root / ".erk" / "pr-files"`
- Line 152: `[".erk/plan/PLAN.md"]` → `[".erk/pr-files/PLAN.md"]`

### `tests/unit/cli/commands/exec/scripts/test_plan_save.py` (lines 230, 241, 244)

In `test_draft_pr_commits_plan_file()`:
- Line 230: docstring `.erk/plan/PLAN.md` → `.erk/pr-files/PLAN.md`
- Line 241: assertion `".erk/plan/PLAN.md"` → `".erk/pr-files/PLAN.md"`
- Line 244: path `".erk" / "plan"` → `".erk" / "pr-files"`

**Verify**: Run `test_plan_save.py` — all tests pass.

---

## Phase 2: Commit Learn Materials to Branch (replaces gist upload)

### `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

The current Step 5 (lines 571-599) uploads learn materials to a gist. Replace with backend-branching logic:

**Add import**: `from erk_shared.plan_store import get_plan_backend`

**After Step 4** (PR review comments, ~line 569), replace Step 5 with:

```
if draft_pr backend AND branch_name is available:
    1. Checkout the plan's branch (from plan-header metadata)
    2. Copy files from learn_dir to .erk/pr-files/learn-materials/
    3. Stage, commit ("Add learn materials for plan #{issue}"), push
    4. Restore original branch (try/finally)
    5. Set workflow_inputs = {"issue_number": ..., "materials_branch": branch_name}
else:
    Existing gist flow unchanged (github backend)
```

The `branch_name` is already parsed in `_get_pr_for_plan_direct()` at line 299. Propagate it to the outer scope (either return it in the result dict or store in a variable before Step 5).

**Update dataclasses** (lines 72-90):
- `TriggerSuccess.gist_url` → `gist_url: str | None`, add `materials_branch: str | None`
- `PreprocessSuccess.gist_url` → same pattern
- Update `_output_success()` and `_output_preprocess_success()` signatures

**Follow the checkout pattern from `plan_save.py`** (lines 146-156): checkout branch in try block, restore in finally.

### `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`

Add tests:
- `test_draft_pr_backend_commits_to_branch` — verify files committed to `.erk/pr-files/learn-materials/`, no gist created, workflow triggered with `materials_branch`
- `test_github_backend_uses_gist` — verify existing gist flow for default backend

---

## Phase 3: Update learn.yml Workflow and /erk:learn Skill

### `.github/workflows/learn.yml`

Add `materials_branch` as optional input (make `gist_url` optional too):

```yaml
gist_url:
  description: "URL of gist containing preprocessed learn materials"
  required: false
  type: string
  default: ""
materials_branch:
  description: "Branch with learn materials in .erk/pr-files/learn-materials/"
  required: false
  type: string
  default: ""
```

Add a step before "Run learn workflow" to checkout materials from the branch:

```yaml
- name: Checkout materials from branch
  if: inputs.materials_branch != ''
  run: |
    git fetch origin "${{ inputs.materials_branch }}"
    git checkout "${{ inputs.materials_branch }}" -- .erk/pr-files/learn-materials/
```

Update the learn invocation to pass `materials_branch` when available (instead of `gist_url`).

### `.claude/commands/erk/learn.md`

In Step 2 ("Check for Preprocessed Materials"), add a new path:

**When `materials_branch` is provided:**
1. Materials are already on filesystem at `.erk/pr-files/learn-materials/` (checked out by workflow)
2. Copy files to session learn directory: `cp .erk/pr-files/learn-materials/* .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/`
3. Skip to Step 4 (same as gist_url path — analysis agents)

Existing `gist_url` path and "no parameters" path remain unchanged.

---

## Phase 4: Add `.erk/pr-files/` Cleanup to plan-implement.yml

### `.github/workflows/plan-implement.yml`

After the existing "Clean up .worker-impl/ after implementation" step (lines 377-392), add:

```yaml
- name: Clean up .erk/pr-files/ after implementation
  if: <same condition as .worker-impl cleanup>
  env:
    BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
    SUBMITTED_BY: ${{ inputs.submitted_by }}
  run: |
    git fetch origin "$BRANCH_NAME"
    git reset --hard "origin/$BRANCH_NAME"
    if [ -d .erk/pr-files/ ]; then
      git config user.name "$SUBMITTED_BY"
      git config user.email "$SUBMITTED_BY@users.noreply.github.com"
      git rm -rf .erk/pr-files/
      git commit -m "Remove .erk/pr-files/ after implementation"
      git push origin "$BRANCH_NAME"
      echo "Cleaned up .erk/pr-files/"
    fi
```

---

## Phase 5: Add Land Validation for `.erk/pr-files/`

### `src/erk/cli/commands/land_pipeline.py`

Add `validate_pr_files_cleaned` step:

```python
def validate_pr_files_cleaned(ctx: ErkContext, state: LandState) -> LandState | LandError:
    """Validate .erk/pr-files/ has been cleaned up after implementation."""
    # Only applies to draft_pr backend
    if ctx.plan_store.get_provider_name() != "github-draft-pr":
        return state

    pr_files_path = state.repo_root / ".erk" / "pr-files"
    if pr_files_path.exists():
        return LandError(
            phase="validate_pr_files_cleaned",
            error_type="pr_files_not_cleaned",
            message=(
                ".erk/pr-files/ still exists on the branch.\n\n"
                "This directory should have been removed after implementation.\n"
                "Run 'git rm -rf .erk/pr-files/' and commit to clean up."
            ),
            details={"branch": state.branch},
        )
    return state
```

Insert in `_validation_pipeline()` between `validate_pr` and `check_learn_status`:

```python
def _validation_pipeline() -> tuple[LandStep, ...]:
    return (
        resolve_target,
        validate_pr,
        validate_pr_files_cleaned,  # NEW
        check_learn_status,
        gather_confirmations,
        resolve_objective,
    )
```

**Note**: Filesystem check works for current-branch landing (the common case for draft_pr plans). For PR-number landing from a different branch, would need `git ls-tree` — acceptable as a future enhancement.

### Tests

Add to `tests/unit/cli/commands/land/`:
- Test `validate_pr_files_cleaned` returns `LandError` when `.erk/pr-files/` exists
- Test it passes when directory absent
- Test it skips for non-draft_pr backends

---

## Verification

1. **Phase 1**: Run `pytest tests/unit/cli/commands/exec/scripts/test_plan_save.py`
2. **Phase 2**: Run `pytest tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`
3. **Phase 5**: Run `pytest tests/unit/cli/commands/land/` for new validation tests
4. **Full CI**: `make fast-ci`
5. **End-to-end**: Create a plan with `draft_pr` backend, trigger learn, verify materials appear on branch under `.erk/pr-files/learn-materials/`, implement, verify cleanup, land successfully

## What This Does NOT Change

- **GitHub (issues) backend**: Gist flow unchanged — `upload_learn_materials.py`, `download_learn_materials.py`, gist gateway methods all remain
- **Session upload** (`upload_session.py`): Still uses gists for now — separate follow-up
- **Metadata schema**: Existing gist fields remain (used by github backend). May add `learn_materials_branch` field if needed during implementation
- **Delimiter packing code**: Stays in place for github backend use