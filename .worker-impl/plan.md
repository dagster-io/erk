# Plan: Create DraftPRPlanBackend

**Part of Objective #7419, Step 1.2**

## Context

The plan system currently stores plans as GitHub issues (`GitHubPlanStore` composes `GitHubIssues`). Objective #7419 migrates the system of record to draft PRs. Step 1.2 creates the `DraftPRPlanBackend` — a second `PlanBackend` implementation that uses draft PRs instead of issues.

The existing `GitHub` ABC already has all needed PR methods: `create_pr(draft=True)`, `get_pr()`, `get_pr_for_branch()`, `close_pr()`, `update_pr_body()`, `create_pr_comment()`, `add_label_to_pr()`, etc. No new gateway is needed.

## Design Decisions

1. **Composes `GitHub` ABC** (not a sub-gateway) — all PR methods already exist on the top-level `GitHub` ABC. Creating a sub-gateway would be over-engineering.

2. **PR body = metadata block + plan content** — single document, one API call for reads. Uses same `<!-- plan-header ... -->` YAML block format as issues. Plan content follows after the metadata block.

3. **Plan ID = PR number as string** — consistent with issue-based approach where plan ID = issue number as string.

4. **`resolve_plan_id_for_branch` requires API call** — unlike issues (zero-cost regex on P-prefix branch names), draft PRs require `get_pr_for_branch()` to resolve branch → PR number. The ABC docstring already documents this: "Future backends (e.g., DraftPRPlanBackend) may require an API call."

5. **`erk-plan` label on PRs** — identifies plan PRs vs regular draft PRs. Applied via `add_label_to_pr()` after creation.

6. **`branch_name` required in metadata for `create_plan`** — draft PRs require an existing pushed branch. The branch name is passed via the metadata dict.

## Implementation

### Phase 1: Enhance FakeGitHub for PR state management

FakeGitHub currently doesn't maintain state across PR mutations (e.g., `create_pr()` returns hardcoded 999 and doesn't register in `_pr_details`). The `PlanBackend` interface tests require create→get roundtrips. Enhance FakeGitHub minimally:

**File: `packages/erk-shared/src/erk_shared/gateway/github/fake.py`**

- Add `_next_pr_number` counter starting at **999** (preserves existing tests that assert `pr_number == 999` — they only create one PR each)
- In `create_pr()`, auto-register a `PRDetails` in `_pr_details` and `_prs_by_branch` with the current branch/title/body/draft state
- In `update_pr_body()`, update the stored `PRDetails` body (via `dataclasses.replace`) so `get_pr()` returns latest state
- Keep all existing mutation tracking (`_created_prs`, `_updated_pr_bodies`, etc.)
- Affected existing tests: `tests/commands/submit/test_pr_creation.py` (asserts `== 999`), `tests/commands/submit/test_learn_plans.py` (asserts `== 999`) — these will continue to pass since they create only one PR

### Phase 2: Create DraftPRPlanBackend

**New file: `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py`**

```python
class DraftPRPlanBackend(PlanBackend):
    def __init__(self, github: GitHub): ...
```

**Method implementations:**

| Method | Implementation |
|--------|---------------|
| `get_provider_name()` | Return `"github-draft-pr"` |
| `create_plan()` | `create_pr(draft=True)` with metadata+content body, then `add_label_to_pr("erk-plan")`. Requires `branch_name` in metadata. |
| `get_plan()` | `get_pr()` → parse body → split metadata block from plan content → convert to `Plan` |
| `get_plan_for_branch()` | `get_pr_for_branch()` → convert PRDetails to Plan |
| `resolve_plan_id_for_branch()` | `get_pr_for_branch()` → return PR number as string, or None if not found |
| `list_plans()` | `list_prs()` → filter by `is_draft` → `get_pr()` for each to check label + extract metadata |
| `close_plan()` | `create_pr_comment()` with close message → `close_pr()` |
| `update_metadata()` | `get_pr()` → `replace_metadata_block_in_body()` → `update_pr_body()` |
| `update_plan_content()` | `get_pr()` → replace content after metadata block → `update_pr_body()` |
| `add_comment()` | `create_pr_comment()`, return comment ID as string |
| `post_event()` | `add_comment()` (if comment provided) + `update_metadata()` |
| `get_metadata_field()` | `get_pr()` → parse body → `find_metadata_block()` → extract field |
| `get_all_metadata_fields()` | `get_pr()` → parse body → `find_metadata_block()` → return all fields |

**PR body format:**
```
<!-- plan-header
schema_version: "2"
created_at: "2024-01-15T10:00:00Z"
created_by: "username"
-->

# Plan: Title

Plan content here...
```

**Conversion helper in `packages/erk-shared/src/erk_shared/plan_store/conversion.py`:**
- Add `pr_details_to_plan(pr: PRDetails, *, plan_body: str | None) -> Plan` — parallel to existing `issue_info_to_plan()`

### Phase 3: Tests

**Parameterize interface tests: `tests/unit/plan_store/test_plan_backend_interface.py`**
- Change `plan_backend` fixture to `@pytest.fixture(params=["github_issues", "draft_pr"])`
- Both backends run through the same interface contract tests

**New test file: `tests/unit/plan_store/test_draft_pr_backend.py`**
- Branch resolution tests (`resolve_plan_id_for_branch`, `get_plan_for_branch`)
- PR-specific behavior (label application, draft flag)
- Metadata block in PR body parsing

**New integration test: `tests/integration/plan_store/test_draft_pr_plan_store.py`**
- Branch → plan resolution with mocked API responses

### Phase 4: Enhance FakeGitHub tests

**File: `tests/unit/fakes/test_fake_github.py`** (or existing fake tests)
- Verify create_pr → get_pr roundtrip
- Verify update_pr_body updates stored state
- Verify incrementing PR numbers

## Files to Modify

| File | Change |
|------|--------|
| `packages/erk-shared/src/erk_shared/plan_store/draft_pr.py` | **NEW** — DraftPRPlanBackend class |
| `packages/erk-shared/src/erk_shared/plan_store/conversion.py` | Add `pr_details_to_plan()` |
| `packages/erk-shared/src/erk_shared/gateway/github/fake.py` | Enhance PR state management |
| `tests/unit/plan_store/test_plan_backend_interface.py` | Parameterize for both backends |
| `tests/unit/plan_store/test_draft_pr_backend.py` | **NEW** — DraftPR-specific tests |
| `tests/integration/plan_store/test_draft_pr_plan_store.py` | **NEW** — Integration tests |

## Existing Code to Reuse

- `find_metadata_block()` / `render_metadata_block()` / `replace_metadata_block_in_body()` from `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py`
- `PlanHeaderSchema` from `packages/erk-shared/src/erk_shared/gateway/github/metadata/schemas.py`
- `Plan`, `PlanNotFound`, `CreatePlanResult` types from `packages/erk-shared/src/erk_shared/plan_store/types.py`
- `PRDetails`, `PRNotFound` types from `packages/erk-shared/src/erk_shared/gateway/github/types.py`

## Verification

1. Run parameterized interface tests: `pytest tests/unit/plan_store/test_plan_backend_interface.py`
2. Run DraftPR-specific tests: `pytest tests/unit/plan_store/test_draft_pr_backend.py`
3. Run integration tests: `pytest tests/integration/plan_store/test_draft_pr_plan_store.py`
4. Run FakeGitHub tests to verify enhancement doesn't break existing tests: `pytest tests/unit/fakes/`
5. Type check: `ty`
6. Lint: `ruff check`