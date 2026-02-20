<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- WARNING: Machine-generated. Manual edits may break erk tooling. -->
<!-- erk:metadata-block:plan-header -->
<details>
<summary><code>plan-header</code></summary>

```yaml

schema_version: '2'
created_at: '2026-02-20T05:32:02.126448+00:00'
created_by: schrockn
plan_comment_id: null
last_dispatched_run_id: '22220842439'
last_dispatched_node_id: WFR_kwLOPxC3hc8AAAAFLHclxw
last_dispatched_at: '2026-02-20T10:39:01.003810+00:00'
last_local_impl_at: null
last_local_impl_event: null
last_local_impl_session: null
last_local_impl_user: null
last_remote_impl_at: null
last_remote_impl_run_id: null
last_remote_impl_session_id: null
branch_name: plan-plan-support-draft-pr-mode-02-20-0531
created_from_session: 4d94fd6e-e691-409e-bae1-3771fd697459

```

</details>
<!-- /erk:metadata-block:plan-header -->

---

<details>
<summary><code>original-plan</code></summary>

# Plan: Support Draft PR Mode in Replan

## Context

The `/erk:replan` command creates updated plans from existing ones, but it hardcodes GitHub issue operations (`gh issue view`, `gh issue close`, `gh issue edit`). When `ERK_PLAN_BACKEND="draft_pr"`, plans are stored as draft PRs, not issues. The replan command currently cannot fetch, close, or label draft-PR-backed plans.

Some exec scripts (`get-plan-metadata`, `close-issue-with-comment`) already use `require_plan_backend(ctx)` and work with both backends. The fix: create equivalent backend-aware exec scripts for the remaining operations, then update `replan.md`.

## Changes

### 1. Add `add_label` to PlanBackend ABC

**File:** `packages/erk-shared/src/erk_shared/plan_store/backend.py`

Add abstract method:
```python
@abstractmethod
def add_label(self, repo_root: Path, plan_id: str, label: str) -> None: ...
```

Both underlying gateways already have label support:
- `GitHubIssues.ensure_label_on_issue()` (abc.py:215, fake.py:357)
- `GitHub.add_label_to_pr()` (abc.py:528, fake.py:815)

### 2. Implement `add_label` in both backends

**`packages/erk-shared/src/erk_shared/plan_store/github.py`** - GitHubPlanStore:
```python
def add_label(self, repo_root, plan_id, label):
    self._github_issues.ensure_label_on_issue(repo_root, int(plan_id), label)
```

**`packages/erk-shared/src/erk_shared/plan_store/draft_pr.py`** - DraftPRPlanBackend:
```python
def add_label(self, repo_root, plan_id, label):
    self._github.add_label_to_pr(repo_root, int(plan_id), label)
```

### 3. Create `get-plan-info` exec script

**New file:** `src/erk/cli/commands/exec/scripts/get_plan_info.py`

Backend-aware plan info retrieval wrapping `PlanBackend.get_plan()`. Returns JSON:
```json
{"success": true, "plan_id": "42", "title": "...", "state": "OPEN", "labels": [...], "url": "...", "objective_id": null, "backend": "github"}
```

With `--include-body` flag, adds `"body": "..."` containing plan content.

Uses the existing pattern from `get_plan_metadata.py`:
- `require_plan_backend(ctx)` for backend resolution
- `require_repo_root(ctx)` for repo root
- `PlanNotFound` check with exit code 1

### 4. Create `add-plan-label` exec script

**New file:** `src/erk/cli/commands/exec/scripts/add_plan_label.py`

Backend-aware label addition wrapping `PlanBackend.add_label()`. Arguments: plan number + `--label` option.

### 5. Register both scripts in group.py

**File:** `src/erk/cli/commands/exec/group.py`

Add imports and `exec_group.add_command()` calls for both new scripts.

### 6. Update `replan.md`

**File:** `.claude/commands/erk/replan.md`

Four targeted changes:

| Location | Before | After |
|----------|--------|-------|
| **Step 2** (line ~48) | `erk exec get-issue-body <number>` | `erk exec get-plan-info <number>` |
| **Step 4a** (lines ~138-146) | `gh issue view <number> --comments --json comments --jq '.comments[0].body'` + manual metadata-block parsing | `erk exec get-plan-info <number> --include-body` + parse `body` from JSON |
| **Step 7.4** (line ~403) | `gh issue edit <new_number> --add-label "erk-consolidated"` | `erk exec add-plan-label <new_number> --label "erk-consolidated"` |
| **Step 7.5** (lines ~411-419) | `gh issue close <original> --comment "..."` | `erk exec close-issue-with-comment <original> --comment "..."` (already exists, already backend-aware) |

Also simplify Step 4a parsing instructions: remove the `<!-- erk:metadata-block:plan-body -->` comment-parsing logic. The `get-plan-info --include-body` script handles backend-specific extraction internally.

Update terminology: "issue" -> "plan" where referring to the generic concept (keep "issue" where it refers specifically to GitHub issues, e.g. URL parsing in Step 1).

### 7. Tests

**New file:** `tests/unit/cli/commands/exec/scripts/test_get_plan_info.py`
- `test_get_plan_info_success` - FakeGitHubIssues with seeded issue, verify JSON fields
- `test_get_plan_info_draft_pr_backend` - DraftPRPlanBackend with created plan, verify JSON fields including `backend: "github-draft-pr"`
- `test_get_plan_info_include_body` - verify body field present with `--include-body`
- `test_get_plan_info_excludes_body_by_default` - verify no body field without flag
- `test_get_plan_info_not_found` - exit code 1, error JSON

**New file:** `tests/unit/cli/commands/exec/scripts/test_add_plan_label.py`
- `test_add_plan_label_success` - verify label added via FakeGitHubIssues
- `test_add_plan_label_draft_pr_backend` - verify label added via FakeGitHub PR labels
- `test_add_plan_label_requires_label_flag` - missing `--label` exits with code 2

**Existing file:** `tests/unit/plan_store/test_plan_backend_interface.py`
- Add `test_add_label_adds_label` using `backend_with_plan` fixture (runs for both backends)
- Add `test_add_label_not_found_raises_runtime_error` using `plan_backend` fixture

## Key Files

| File | Action |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/backend.py` | Add `add_label` abstract method |
| `packages/erk-shared/src/erk_shared/plan_store/github.py` | Implement `add_label` |
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` | Implement `add_label` |
| `src/erk/cli/commands/exec/scripts/get_plan_info.py` | New: backend-aware plan info |
| `src/erk/cli/commands/exec/scripts/add_plan_label.py` | New: backend-aware label addition |
| `src/erk/cli/commands/exec/group.py` | Register both new scripts |
| `.claude/commands/erk/replan.md` | Update 4 locations to use backend-aware commands |
| `tests/unit/cli/commands/exec/scripts/test_get_plan_info.py` | New: 5 tests |
| `tests/unit/cli/commands/exec/scripts/test_add_plan_label.py` | New: 3 tests |
| `tests/unit/plan_store/test_plan_backend_interface.py` | Add 2 interface tests for `add_label` |

## Verification

1. Run unit tests for new exec scripts:
   ```
   pytest tests/unit/cli/commands/exec/scripts/test_get_plan_info.py
   pytest tests/unit/cli/commands/exec/scripts/test_add_plan_label.py
   ```
2. Run interface tests to verify both backends implement `add_label`:
   ```
   pytest tests/unit/plan_store/test_plan_backend_interface.py
   ```
3. Run full plan store test suite:
   ```
   pytest tests/unit/plan_store/
   ```
4. Type check and lint:
   ```
   make fast-ci
   ```


</details>
---


To checkout this PR in a fresh worktree and environment locally, run:

```
source "$(erk pr checkout 7648 --script)" && erk pr sync --dangerous
```
