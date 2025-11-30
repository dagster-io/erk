# Plan: Eliminate .worker-impl/ - Reconstruct .impl/ from GitHub Issue

## Summary

Eliminate the `.worker-impl/` folder entirely by having GitHub Actions reconstruct `.impl/` directly from the GitHub issue. The GitHub issue becomes the single source of truth for plan content, with no plan files committed to the branch.

## Current vs Target Flow

**Current:**
```
erk submit → create .worker-impl/ → commit → push → workflow copies to .impl/ → cleanup commit
```

**Target:**
```
erk submit → empty commit → push → workflow reconstructs .impl/ from issue → done
```

## Implementation Steps

### Step 1: Create `create-impl-from-issue` Kit CLI Command

**Create:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_impl_from_issue.py`

Pattern from `create_worker_impl_from_issue.py` but:
- Call `create_impl_folder()` from `impl_folder.py` (not `create_worker_impl_folder`)
- Call `save_issue_reference()` to create `.impl/issue.json`
- Output `impl_path` instead of `worker_impl_path`

```python
@click.command(name="create-impl-from-issue")
@click.argument("issue_number", type=int)
@click.argument("issue_title")
@click.option("--repo-root", type=click.Path(...), default=None)
def create_impl_from_issue(issue_number: int, issue_title: str, repo_root: Path | None) -> None:
    """Create .impl/ folder from GitHub issue with plan content."""
    repo_root = repo_root or Path.cwd()

    # Fetch plan from GitHub issue
    github_issues = RealGitHubIssues()
    plan_store = GitHubPlanStore(github_issues)
    plan = plan_store.get_plan(repo_root, str(issue_number))

    # Create .impl/ using existing function
    impl_path = create_impl_folder(repo_root, plan.body)

    # Add issue.json reference
    save_issue_reference(impl_path, issue_number, plan.url)

    # Output JSON result
    click.echo(json.dumps({
        "success": True,
        "impl_path": str(impl_path),
        "issue_number": issue_number,
        "issue_url": plan.url,
    }))
```

**Update:** `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml` - Add command entry

### Step 2: Modify `erk submit` Command

**File:** `src/erk/cli/commands/submit.py`

**Remove:**
- Import of `create_worker_impl_folder`
- Plan fetching (`ctx.plan_store.get_plan()`)
- `.worker-impl/` folder creation
- Staging `.worker-impl/`

**Change commit to:**
```python
# Create empty commit to establish branch for PR
ctx.git.commit(
    repo.root,
    f"Initialize implementation for issue #{issue_number}",
    allow_empty=True
)
```

**Check if git integration supports `allow_empty`:** If not, add parameter to `GitOperations.commit()` in `src/erk/core/integrations/git.py`.

### Step 3: Simplify GitHub Actions Workflow

**File:** `.github/workflows/dispatch-erk-queue-git.yml`

**Phase 2 changes (lines ~119-155):**

Remove `.worker-impl/` update block. After checkout, add:
```yaml
- name: Reconstruct .impl/ from GitHub issue
  env:
    ISSUE_NUMBER: ${{ inputs.issue_number }}
    GH_TOKEN: ${{ github.token }}
  run: |
    source $HOME/.cargo/env
    ISSUE_TITLE=$(gh issue view "$ISSUE_NUMBER" --json title -q .title)

    # Remove stale .impl/ if exists (for reruns)
    rm -rf .impl

    # Reconstruct from issue
    dot-agent run erk create-impl-from-issue "$ISSUE_NUMBER" "$ISSUE_TITLE"

    # Add run-info.json
    cat > .impl/run-info.json <<EOF
    {
      "run_id": "${{ github.run_id }}",
      "run_url": "${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}"
    }
    EOF
```

**Phase 4 changes (lines ~232-243):**

Remove "Set up implementation folder" step (the copy from `.worker-impl/` to `.impl/`). Already handled above.

**Phase 5 changes (lines ~274-306):**

Remove these lines:
```yaml
git reset HEAD .worker-impl/   # No longer needed
git rm -rf .worker-impl/       # No longer needed
git commit -m "Remove .worker-impl/ folder after implementation"  # No longer needed
```

### Step 4: Remove CI Skip Action

**Delete:** `.github/actions/check-worker-impl/action.yml`

**Update these workflows** to remove `check-worker-impl` usage:
- `.github/workflows/test.yml`
- `.github/workflows/lint.yml`
- `.github/workflows/pyright.yml`
- `.github/workflows/prettier.yml`
- `.github/workflows/check-sync.yml`
- `.github/workflows/md-check.yml`

For each: remove the `check-submission` job and any `needs: check-submission` / `if: needs.check-submission.outputs.skip == 'false'` conditions.

### Step 5: Delete Obsolete Code

**Delete files:**
- `packages/erk-shared/src/erk_shared/worker_impl_folder.py`
- `tests/packages/erk_shared/test_worker_impl_folder.py`
- `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/create_worker_impl_from_issue.py`
- `packages/dot-agent-kit/tests/unit/kits/erk/test_create_worker_impl_from_issue.py` (if exists)

**Update kit.yaml:** Remove `create-worker-impl-from-issue` entry

### Step 6: Update Documentation

**File:** `docs/agent/plan-lifecycle.md`

- Remove `.worker-impl/` from "Key File Locations at a Glance" table
- Update Phase 2 (Plan Submission) - no folder creation, just empty commit
- Update Phase 3 (Workflow Dispatch) - `.impl/` reconstructed from issue
- Remove Phase 5 cleanup commit references
- Update diagrams to remove `.worker-impl/` → `.impl/` copy step

**File:** `docs/agent/planning-workflow.md` (if it references `.worker-impl/`)

## Files Summary

### Create
| File | Purpose |
|------|---------|
| `packages/dot-agent-kit/.../create_impl_from_issue.py` | New kit CLI command |
| `packages/dot-agent-kit/tests/.../test_create_impl_from_issue.py` | Tests for new command |

### Delete
| File | Reason |
|------|--------|
| `.github/actions/check-worker-impl/action.yml` | No `.worker-impl/` to check |
| `packages/erk-shared/.../worker_impl_folder.py` | Entire module obsolete |
| `tests/packages/erk_shared/test_worker_impl_folder.py` | Tests for obsolete module |
| `packages/dot-agent-kit/.../create_worker_impl_from_issue.py` | Replaced |

### Modify
| File | Changes |
|------|---------|
| `src/erk/cli/commands/submit.py` | Remove `.worker-impl/` creation, use empty commit |
| `src/erk/core/integrations/git.py` | Add `allow_empty` param if needed |
| `.github/workflows/dispatch-erk-queue-git.yml` | Reconstruct `.impl/` from issue |
| `.github/workflows/*.yml` (6 files) | Remove CI skip logic |
| `packages/dot-agent-kit/.../kit.yaml` | Update command registry |
| `docs/agent/plan-lifecycle.md` | Update documentation |

## Testing Strategy

1. **Unit tests** for `create-impl-from-issue`:
   - Success: creates `.impl/` with `plan.md`, `progress.md`, `issue.json`
   - Error: plan not found returns error JSON

2. **Integration test** for submit flow:
   - Verify empty commit created
   - Verify PR created without plan files

3. **Manual E2E test**:
   - Run `erk submit` → verify workflow reconstructs `.impl/` → verify implementation succeeds

## Risks

1. **Git `allow_empty` support** - May need to add parameter to git integration
2. **Reruns** - Actually simpler: always reconstruct fresh from issue (no stale data)
3. **In-flight implementations** - Existing PRs with `.worker-impl/` will still work (workflow handles both cases until we remove the code)