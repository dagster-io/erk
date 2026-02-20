# Use `.erk/impl-context/` directly, then delete it

## Context

`.erk/impl-context/` is created during draft-PR plan saving and committed to the plan branch. It contains the original plan content (`plan.md`) and metadata (`ref.json`). Currently, `setup-impl-from-issue` ignores these local files and instead calls `plan_backend.get_plan()`, which round-trips through the GitHub API to fetch the plan content from the PR body — content that was extracted FROM `.erk/impl-context/plan.md` in the first place. After implementation, `.erk/impl-context/` is never cleaned up and gets merged into trunk.

**Goal**: For draft-PR plans, read plan content directly from `.erk/impl-context/` after branch checkout, then delete it. Eliminate the `get_plan()` call for draft-PR plans in `setup-impl-from-issue`.

## Changes

### 1. Enrich `ref.json` during plan-save

**File:** `src/erk/cli/commands/exec/scripts/plan_save.py` (lines 168-176)

Add `title` to `ref.json`. Currently it only stores `provider` and `objective_id`.

```python
# Current
ref_data: dict[str, str | int | None] = {
    "provider": "github-draft-pr",
    "url": None,
}

# New
ref_data: dict[str, str | int | None] = {
    "provider": "github-draft-pr",
    "title": title,
}
```

Remove `url` (it's always `None` since the PR hasn't been created yet). Add `title` which IS known at commit time. `objective_id` handling stays the same.

### 2. Refactor `setup-impl-from-issue` for draft-PR plans

**File:** `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py`

Replace `plan_backend.get_plan()` with a two-phase approach:

**Phase A — Branch discovery**: Use `github.get_pr(repo_root, issue_number)` directly (one REST call). We only need `head_ref_name` and `url` from the response — not the parsed plan body.

**Phase B — After checkout**: If `.erk/impl-context/plan.md` exists, read plan content and metadata from it instead of from the PR body. Then delete the directory with `shutil.rmtree()`.

**Fallback**: If `.erk/impl-context/` doesn't exist after checkout (legacy branch, already cleaned up), extract plan content from `pr.body` using `extract_plan_content()` — same as the current `_convert_to_plan()` does.

New imports needed:
- `require_github` from `erk_shared.context.helpers`
- `PRNotFound` from `erk_shared.gateway.github.types`
- `IMPL_CONTEXT_DIR` from `erk_shared.plan_store.draft_pr_lifecycle`
- `extract_plan_content` from `erk_shared.plan_store.draft_pr_lifecycle` (for fallback)

Rough structure of the draft-PR branch:
```python
github = require_github(ctx)
plan_backend = require_plan_backend(ctx)

if plan_backend.get_provider_name() == "github-draft-pr":
    # Draft-PR: lightweight PR query for branch name only
    pr_result = github.get_pr(repo_root, issue_number)
    if isinstance(pr_result, PRNotFound):
        # error handling...
    branch_name = pr_result.head_ref_name
    pr_url = pr_result.url

    # ... checkout branch (existing logic) ...

    impl_context_dir = repo_root / IMPL_CONTEXT_DIR
    impl_context_plan = impl_context_dir / "plan.md"

    if impl_context_plan.exists():
        # Read from local files
        plan_content = impl_context_plan.read_text(encoding="utf-8")
        ref_json = json.loads((impl_context_dir / "ref.json").read_text(encoding="utf-8"))
        objective_id = ref_json.get("objective_id")
        # Clean up
        shutil.rmtree(impl_context_dir)
    else:
        # Fallback: extract from PR body
        plan_content = extract_plan_content(pr_result.body)
        objective_id = ...  # extract from PR metadata

    # Create .impl/ using plan_content
    create_impl_folder(worktree_path=cwd, plan_content=plan_content, overwrite=True)
    save_plan_ref(impl_path, provider="github-draft-pr", plan_id=str(issue_number),
                  url=pr_url, labels=(), objective_id=objective_id)
else:
    # Issue-based plan: existing flow via get_plan()
    result = plan_backend.get_plan(repo_root, str(issue_number))
    # ... rest of existing code unchanged ...
```

The issue-based plan path remains completely unchanged.

### 3. CI Workflow: Use `.erk/impl-context/` directly

**File:** `.github/workflows/plan-implement.yml`

After the branch checkout step (line 136), check if `.erk/impl-context/` exists. If so, copy plan content directly to `.worker-impl/` (or skip `.worker-impl/` entirely and go straight to `.impl/`). Then `git rm` the directory.

Extend the existing "Remove .worker-impl/ from git tracking" step (lines 191-203) to also remove `.erk/impl-context/`:

```yaml
- name: Remove plan staging dirs from git tracking
  run: |
    NEEDS_CLEANUP=false
    git config user.name "$SUBMITTED_BY"
    git config user.email "$SUBMITTED_BY@users.noreply.github.com"
    if [ -d .worker-impl/ ]; then
      git rm -rf .worker-impl/
      NEEDS_CLEANUP=true
    fi
    if [ -d .erk/impl-context/ ]; then
      git rm -rf .erk/impl-context/
      NEEDS_CLEANUP=true
    fi
    if [ "$NEEDS_CLEANUP" = true ]; then
      git commit -m "Remove plan staging dirs before implementation"
      git push origin "$BRANCH_NAME"
    fi
```

Also extend the post-implementation cleanup step (lines 377-392) with the same pattern as belt-and-suspenders.

### 4. Local agent instructions: Add cleanup step

**File:** `.claude/commands/erk/plan-implement.md`

Add Step 2d after Step 2c to clean up `.erk/impl-context/` from git tracking if it wasn't already removed by `setup-impl-from-issue` (e.g., for the `shutil.rmtree` case where the directory was deleted locally but not from git):

```markdown
### Step 2d: Clean Up Plan Staging Directory

If `.erk/impl-context/` exists in git tracking, remove it:

\```bash
if [ -d .erk/impl-context/ ]; then
  git rm -rf .erk/impl-context/
  git commit -m "Remove .erk/impl-context/ before implementation"
  git push origin "$(git branch --show-current)"
fi
\```
```

Update the note at line 273 (Step 12) to mention `.erk/impl-context/` cleanup.

### 5. Update tests for `setup-impl-from-issue`

**File:** `tests/unit/cli/commands/exec/scripts/test_plan_save.py` and corresponding test for `setup_impl_from_issue`

- Update `test_plan_save` to verify `title` is written to `ref.json`
- Add test cases for `setup-impl-from-issue` with `.erk/impl-context/` present on branch
- Add test case for fallback path when `.erk/impl-context/` doesn't exist

## Files Modified

| File | Change |
|------|--------|
| `src/erk/cli/commands/exec/scripts/plan_save.py` | Add `title` to `ref.json`, remove unused `url: None` |
| `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` | Use `github.get_pr()` + `.erk/impl-context/` for draft-PR plans |
| `.github/workflows/plan-implement.yml` | Add `.erk/impl-context/` to both cleanup steps |
| `.claude/commands/erk/plan-implement.md` | Add Step 2d + update Step 12 note |
| `tests/unit/cli/commands/exec/scripts/test_plan_save.py` | Verify `title` in ref.json |
| `tests/unit/cli/commands/exec/scripts/test_setup_impl_from_issue.py` | Test `.erk/impl-context/` read + fallback |

## Verification

1. Run existing tests for `plan_save` and `setup_impl_from_issue` to ensure no regressions
2. Verify `ref.json` now contains `title` field after plan-save
3. Verify `setup-impl-from-issue` reads from `.erk/impl-context/` when present and falls back to PR body when absent
4. Verify `.erk/impl-context/` is deleted after use
5. Read the modified workflow YAML and verify shell logic handles all directory existence combinations
