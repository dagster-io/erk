# Plan: Objective #8365 Node 2.1 — Update plan-implement.yml to Eliminate .impl/ Copy

## Context

Part of **Objective #8365** (Eliminate .impl/ Folder — Unify on .erk/impl-context/), **Node 2.1**.

The `plan-implement.yml` workflow currently copies `.erk/impl-context/` to `.impl/` so Claude can read plan files during implementation, then deletes `.erk/impl-context/` from git. This copy is redundant: using `git rm --cached` untracks files from git while keeping them on disk (they're already in `.gitignore`), so Claude can read directly from `.erk/impl-context/`.

**Prerequisite:** Phase 1 (PR #8366) must be merged first. It replaces all hardcoded `cwd / ".impl"` paths with `resolve_impl_dir()` and removes the `.impl/` legacy fallback.

## Changes

### 1. Add `has_tracked_files` to GitStatusOps gateway (5-place pattern)

`cleanup_impl_context.py` needs to know if `.erk/impl-context/` has tracked files before deciding whether to delete. This requires a new read-only query method on the status ops gateway.

**1a. ABC** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/abc.py`
- Add `has_tracked_files(self, repo_root: Path, path: str) -> bool`
- Docstring: Check if any files under a relative path are tracked in the git index

**1b. Real** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/real.py`
- Implement via `subprocess.run(["git", "ls-files", path], cwd=repo_root, ...)`
- Return `bool(result.stdout.strip())` (True if any output = files are tracked)
- Use `check=False`, handle non-zero return as False

**1c. Fake** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/fake.py`
- Add `tracked_paths: set[str] | None = None` constructor parameter
- Store as `self._tracked_paths`
- Implement: return `any(tp.startswith(path) for tp in self._tracked_paths)`
- Add `tracked_paths` to `link_state()` signature and body

**1d. FakeGit** `packages/erk-shared/src/erk_shared/gateway/git/fake.py`
- Add `tracked_paths: set[str] | None = None` constructor parameter (~line 200)
- Store as `self._tracked_paths: set[str]`
- Pass to `FakeGitStatusOps` constructor and `link_state` call (~lines 410-422)

**1e. DryRun** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/dry_run.py`
- Pure delegation: `return self._wrapped.has_tracked_files(repo_root, path)`

**1f. Printing** `packages/erk-shared/src/erk_shared/gateway/git/status_ops/printing.py`
- Pure delegation: `return self._wrapped.has_tracked_files(repo_root, path)`

### 2. Update `cleanup_impl_context.py`

**File:** `src/erk/cli/commands/exec/scripts/cleanup_impl_context.py`

After the existence check (`impl_context_exists`), add a tracking check before `shutil.rmtree`:

```python
if not impl_context_exists(repo_root):
    click.echo(json.dumps({"cleaned": False, "reason": "not_found"}))
    return

# Skip cleanup if files exist on disk but are not git-tracked.
# This happens in CI after the workflow runs git rm --cached.
if not git.status.has_tracked_files(repo_root, ".erk/impl-context"):
    click.echo(json.dumps({"cleaned": False, "reason": "not_tracked"}))
    return

# Existing cleanup logic (rmtree + stage + commit + push)...
```

**Why this matters:** Without this check, `cleanup_impl_context` runs `shutil.rmtree(.erk/impl-context/)` which destroys both the flat files AND the branch-scoped `<branch>/plan.md` copy that `setup_impl_from_pr` just created. The plan would be gone before Claude reads it.

### 3. Update `plan-implement.yml`

**File:** `.github/workflows/plan-implement.yml`

**3a. Replace "Set up implementation folder" step** (lines 195-205)

Remove the `cp -r` and write `run-info.json` directly to `.erk/impl-context/`:

```yaml
      - name: Write run metadata to impl-context
        run: |
          cat > .erk/impl-context/run-info.json <<EOF
          {
            "run_id": "${{ github.run_id }}",
            "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
          }
          EOF
          echo "Created .erk/impl-context/run-info.json"
```

**3b. Change "Remove plan staging dirs from git tracking"** (lines 207-223)

Replace `git rm -rf` with `git rm -r --cached`:

```yaml
      - name: Remove plan staging dirs from git tracking
        env:
          BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
          SUBMITTED_BY: ${{ inputs.submitted_by }}
        run: |
          NEEDS_CLEANUP=false
          git config user.name "$SUBMITTED_BY"
          git config user.email "$SUBMITTED_BY@users.noreply.github.com"
          if git ls-files --error-unmatch .erk/impl-context/ >/dev/null 2>&1; then
            git rm -r --cached .erk/impl-context/
            NEEDS_CLEANUP=true
          fi
          if [ "$NEEDS_CLEANUP" = true ]; then
            git commit -m "Remove plan staging dirs before implementation"
            git push origin "$BRANCH_NAME"
            echo "Removed plan staging dirs from git tracking (content preserved on disk)"
          fi
```

Key changes: `git rm -r --cached` (index only), `git ls-files` guard (checks tracking not filesystem), updated echo message.

**3c. Simplify "Clean up plan staging dirs after implementation"** (lines 398-417)

After implementation, `.erk/impl-context/` is untracked. Just delete from disk (CI runner is ephemeral):

```yaml
      - name: Clean up plan staging dirs after implementation
        if: ...
        env:
          BRANCH_NAME: ${{ steps.find_pr.outputs.branch_name }}
          SUBMITTED_BY: ${{ inputs.submitted_by }}
        run: |
          git fetch origin "$BRANCH_NAME"
          git reset --hard "origin/$BRANCH_NAME"
          git config user.name "$SUBMITTED_BY"
          git config user.email "$SUBMITTED_BY@users.noreply.github.com"
          if git ls-files --error-unmatch .erk/impl-context/ >/dev/null 2>&1; then
            git rm -r --cached .erk/impl-context/
            git commit -m "Remove plan staging dirs after implementation"
            git push origin "$BRANCH_NAME"
            echo "Cleaned up plan staging dirs from git tracking"
          else
            echo "No tracked plan staging dirs to clean up"
          fi
```

**3d. Update git status filter** (line 311)

Remove the `.impl/` filter (no longer created by this workflow):

```bash
UNCOMMITTED=$(git status --porcelain | grep -v '^\s*D.*\.erk/impl-context/' || true)
```

### 4. Tests

**4a.** `tests/unit/cli/commands/exec/scripts/test_cleanup_impl_context.py`
- Add `test_cleanup_skips_when_not_tracked`: create `.erk/impl-context/` on disk, configure FakeGit with empty `tracked_paths`. Assert output is `{"cleaned": false, "reason": "not_tracked"}` and no git commits.
- Update existing tests to pass `tracked_paths={".erk/impl-context/"}` to FakeGit so they still exercise the cleanup path.

**4b.** Optionally add a focused unit test for `has_tracked_files` in the fake tests.

## End-to-End Flow After Changes

1. Workflow creates `.erk/impl-context/plan.md`, `ref.json` (committed via `git add -f`)
2. Workflow writes `run-info.json` to `.erk/impl-context/`
3. Workflow runs `git rm -r --cached .erk/impl-context/` + commit + push
4. `.erk/impl-context/` stays on disk, untracked (in `.gitignore`)
5. Claude runs `/erk:plan-implement` which calls `erk exec setup-impl`
6. `setup_impl_from_pr` reads flat `.erk/impl-context/plan.md`, creates branch-scoped copy
7. `cleanup_impl_context` detects files are not tracked, returns `not_tracked`, skips
8. `_validate_impl_folder` finds branch-scoped dir via `resolve_impl_dir()`
9. Claude reads plan and implements

## Known Impacts (Deferred)

- **`pr check --stage=impl`** (`src/erk/cli/commands/pr/check_cmd.py:268-278`): Currently uses `impl_context_dir.exists()` (filesystem check). After this change, it will false-positive since untracked files exist on disk. Should use `has_tracked_files` instead. Defer to a follow-up or include in Phase 2 PR.
- **`plan-implement.md` command** (`.claude/commands/erk/plan-implement.md`): Still references `.impl/plan.md`. This is Node 3.1's scope. The Python code finds the correct path via `resolve_impl_dir()`, but the command text that instructs Claude uses the old path.

## Verification

1. Run unit tests: `pytest tests/unit/cli/commands/exec/scripts/test_cleanup_impl_context.py`
2. Run fast CI: `make fast-ci`
3. Trace the workflow flow mentally: verify `.erk/impl-context/` survives through steps 1-9 above
4. Run full CI: `make all-ci`
