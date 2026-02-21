# Replace Gist Transport with impl-context for Learn Pipeline

## Context

The learn pipeline preprocesses session logs locally, then uploads them to a GitHub gist for the CI workflow to download. This requires:

- Delimiter-based packing/unpacking (fragile, custom format)
- Gist API calls (can fail, rate-limited, size concerns)
- Two dedicated exec scripts just for gist I/O (`upload_learn_materials.py`, `download_learn_materials.py`)

Replace the gist transport with the branch-based `.erk/impl-context/` pattern already used by the draft-PR plan backend: commit learn materials to a dedicated branch, then the CI workflow reads them directly after checkout.

## Approach

### Current flow

```
trigger_async_learn.py:
  preprocess sessions → write to .erk/scratch/learn-{plan_id}/
  pack files with delimiters → upload single gist
  trigger learn.yml with gist_url

learn.yml:
  checkout master → Claude runs /erk:learn with gist_url
  Claude downloads gist → unpacks → analyzes
```

### New flow

```
trigger_async_learn.py:
  preprocess sessions → write to .erk/scratch/learn-{plan_id}/ (unchanged)
  create learn/{plan_id} branch → copy files to .erk/impl-context/
  commit + push branch
  trigger learn.yml with learn_branch

learn.yml:
  checkout learn/{plan_id} branch → Claude runs /erk:learn
  Claude reads .erk/impl-context/ directly (no download, no unpacking)
```

## Detailed Changes

### 1. `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

**Replace gist upload (current Step 5, lines 586-614) with branch-based impl-context:**

Using the same try/finally checkout pattern from `plan_save.py`, but with the git gateway directly (NOT BranchManager — learn branches aren't Graphite-tracked):

```python
# Create learn branch from origin/master
learn_branch = f"learn/{plan_id}"
original_branch = git.branch.get_current_branch(repo_root)
start_point = original_branch or "HEAD"

# Use git gateway directly (not BranchManager — learn branches aren't PR stacks)
git.branch.create_branch(repo_root, learn_branch, "origin/master")
# If branch already exists (re-learn scenario): delete remote and local, recreate

git.branch.checkout_branch(repo_root, learn_branch)
try:
    # Copy preprocessed files to .erk/impl-context/
    impl_context_dir = repo_root / ".erk" / "impl-context"
    impl_context_dir.mkdir(parents=True, exist_ok=True)
    for f in learn_dir.iterdir():
        if f.is_file():
            shutil.copy2(f, impl_context_dir / f.name)

    # Stage, commit, push
    file_paths = [f".erk/impl-context/{f.name}" for f in learn_dir.iterdir() if f.is_file()]
    git.commit.stage_files(repo_root, file_paths)
    git.commit.commit(repo_root, f"Learn materials for plan #{plan_id}")
    git.remote.push_to_remote(repo_root, "origin", learn_branch, set_upstream=True, force=False)
finally:
    git.branch.checkout_branch(repo_root, start_point)
```

**Update dataclasses:**

- `TriggerSuccess`: `gist_url: str` → `learn_branch: str`
- `PreprocessSuccess`: `gist_url: str` → `learn_branch: str`
- `_output_success()`: update parameter
- `_output_preprocess_success()`: update parameter

**Update workflow trigger (current Step 6, lines 621-647):**

- Replace `"gist_url": str(gist_url)` with `"learn_branch": learn_branch` in `workflow_inputs`

**Remove imports:**

- Remove `from erk_shared.gateway.github.abc import GistCreateError`
- Remove `from erk.cli.commands.exec.scripts.upload_learn_materials import combine_learn_material_files`

**Add imports:**

- `import shutil`

### 2. `.github/workflows/learn.yml`

**Replace `gist_url` input with `learn_branch`:**

```yaml
inputs:
  learn_branch:
    description: "Branch containing learn materials in .erk/impl-context/"
    required: true
    type: string
```

**Update checkout step to use the learn branch:**

```yaml
- uses: actions/checkout@v4
  with:
    ref: ${{ inputs.learn_branch }}
    token: ${{ secrets.ERK_QUEUE_GH_PAT }}
    fetch-depth: 0
```

**Update Claude invocation — no gist_url needed:**

```yaml
- name: Run learn workflow
  env:
    PLAN_ID: ${{ inputs.plan_id }}
    WORKFLOW_RUN_URL: ...
  run: |
    claude --print \
      --verbose \
      --model claude-opus-4-6 \
      --output-format stream-json \
      --dangerously-skip-permissions \
      "/erk:learn $PLAN_ID"
```

Remove `GIST_URL` env var entirely.

**Add branch cleanup step (after learn completes):**

```yaml
- name: Cleanup learn branch
  if: always()
  run: git push origin --delete ${{ inputs.learn_branch }} || true
```

### 3. `.claude/commands/erk/learn.md`

**Step 2 (Check for Preprocessed Materials):**

Replace gist detection with impl-context detection:

```
Check if .erk/impl-context/ exists and contains files:

  ls .erk/impl-context/ 2>/dev/null

If files exist:
  - Copy files from .erk/impl-context/ to learn working directory
  - Tell user: "Using preprocessed materials from .erk/impl-context/"
  - Skip to Step 4 (analyze sessions)

If learn_branch parameter provided (interactive mode):
  - git fetch origin {learn_branch}
  - Extract files using git show or create temp worktree
  - Copy to learn working directory
  - Skip to Step 4

Otherwise: proceed to Step 3 (session discovery)
```

**Remove all gist upload references in Step 4** ("Upload to Gist" subsection).

**Update the pipeline display messages** at the top of the command to remove gist references.

### 4. `src/erk/cli/commands/learn/learn_cmd.py`

**Replace `_get_learn_materials_gist_url()` with `_get_learn_materials_branch()`:**

```python
def _get_learn_materials_branch(
    ctx: ErkContext,
    repo_root: Path,
    plan_id: str,
) -> str | None:
    result = ctx.plan_backend.get_metadata_field(repo_root, plan_id, "learn_materials_branch")
    if isinstance(result, PlanNotFound):
        return None
    if not isinstance(result, str):
        return None
    return result
```

**Update the caller** (around line 132-148):

```python
learn_branch = _get_learn_materials_branch(ctx, repo_root, plan_id)
if learn_branch is not None:
    user_output(
        click.style(f"Preprocessed learn materials for plan {plan_id}", bold=True)
        + f"\n\nBranch: {click.style(learn_branch, fg='cyan')}"
        + "\n\nSessions have been preprocessed and committed."
        + "\nClaude will read materials from the branch directly."
    )
    ctx.prompt_executor.execute_interactive(
        worktree_path=repo_root,
        dangerous=dangerous,
        command=f"/erk:learn {plan_id} learn_branch={learn_branch}",
        target_subpath=None,
        permission_mode="edits",
    )
    return
```

### 5. `src/erk/cli/commands/land_cmd.py`

**Replace `_store_learn_materials_gist_url()` with `_store_learn_materials_branch()`:**

```python
def _store_learn_materials_branch(
    ctx: ErkContext,
    *,
    repo_root: Path,
    plan_issue_number: int,
    learn_branch: str,
) -> None:
    plan_id = str(plan_issue_number)
    try:
        ctx.plan_backend.update_metadata(
            repo_root, plan_id, {"learn_materials_branch": learn_branch}
        )
    except PlanHeaderNotFoundError:
        try:
            ctx.plan_backend.add_comment(
                repo_root, plan_id, f"Learn materials branch: {learn_branch}"
            )
        except RuntimeError as comment_err:
            user_output(
                click.style("Warning ", fg="yellow")
                + f"Could not store branch on plan {plan_id}: {comment_err}"
            )
```

**Update the caller** (around line 470-482):

- Parse `learn_branch` from trigger output instead of `gist_url`
- Call `_store_learn_materials_branch()` instead

**Update `LearnPreprocessResult`** dataclass: `gist_url` → `learn_branch`

### 6. `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`

**Replace `learn_materials_gist_url` with `learn_materials_branch`:**

- Update `VALID_PLAN_HEADER_FIELDS` list (line 346)
- Update constant (line 396): `LEARN_MATERIALS_BRANCH: Literal["learn_materials_branch"] = "learn_materials_branch"`
- Update docstring (line 483)
- Update validation block (lines 763-768): validate `learn_materials_branch` as string

### 7. Files to Remove or Simplify

**`src/erk/cli/commands/exec/scripts/upload_learn_materials.py`:**

- Remove `combine_learn_material_files()` function (no longer needed)
- CLI command may still be useful as a standalone gist uploader — evaluate if anything else uses it. If not, remove entirely.

**`src/erk/cli/commands/exec/scripts/download_learn_materials.py`:**

- Remove entirely (delimiter parsing no longer needed)
- Update any exec script registration that references it

### 8. Test Updates

- `tests/unit/cli/commands/land/test_learn_status.py` — update gist_url references to learn_branch
- `tests/shared/github/test_plan_header_extraction.py` — update schema field tests
- `tests/commands/learn/test_display.py` — update display tests
- Any tests for `upload_learn_materials.py` and `download_learn_materials.py` — remove or update

## Verification

1. Run `erk exec trigger-async-learn <plan_id>` and verify:
   - Learn branch created with materials in `.erk/impl-context/`
   - Branch pushed to remote
   - Workflow triggered successfully
2. Check the learn branch on GitHub: `gh api repos/{owner}/{repo}/git/trees/learn/{plan_id} --jq '.tree[].path'`
3. Run the learn.yml workflow and verify it completes (checkout learn branch, Claude reads materials)
4. Verify learn branch is cleaned up after workflow completion
5. Run `erk learn <plan_id>` interactively and verify it detects the learn_materials_branch metadata
6. Run full test suite: `make fast-ci`
