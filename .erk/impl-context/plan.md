# Plan: Objective #7911, Nodes 2.4 + 2.5

Part of Objective #7911 (Delete Issue-Based Plan Backend), Nodes 2.4 and 2.5.

## Context

**Node 2.5 is already complete** — `plan_backend_type` fixtures were removed in PR #8107. Zero matches remain.

**Node 2.4** requires migrating 36 test files that pass `github_issues=` to `ErkContext.for_test()`. This triggers an `issues_explicitly_passed` branch in `context_for_test()` that auto-creates `GitHubPlanStore` for `plan_store`. The goal is to stop this, so all tests default to `PlannedPRBackend`.

## Approach

### Two categories of migration

**Category A (issues-only tests):** Production code uses `require_issues(ctx)` — accesses GitHubIssues directly, never plan_store.

```python
# BEFORE
fake_gh = FakeGitHubIssues(issues={42: issue})
ctx = ErkContext.for_test(github_issues=fake_gh)

# AFTER
fake_gh = FakeGitHubIssues(issues={42: issue})
ctx = ErkContext.for_test(github=FakeGitHub(issues_gateway=fake_gh))
```

No assertion changes — `ctx.issues` still returns `fake_gh`. Only add `FakeGitHub` import.

**Category B (plan_backend tests):** Production code uses `require_plan_backend(ctx)`. PlannedPRBackend methods call `self._github.get_pr()`, so we need PR data seeded instead of issue data.

```python
# BEFORE
fake_gh = FakeGitHubIssues(issues={42: issue_with_metadata_body})
ctx = ErkContext.for_test(github_issues=fake_gh, plan_store=GitHubPlanStore(fake_gh))

# AFTER
fake_github = FakeGitHub(pr_details={42: _make_pr_details(42, "Title", metadata_body)})
ctx = ErkContext.for_test(github=fake_github)
```

Assertion changes:
| FakeGitHubIssues | FakeGitHub | Notes |
|---|---|---|
| `fake_gh.added_comments` `(num, body, id)` | `fake_github.pr_comments` `(num, body)` | No comment_id in tuple |
| `fake_gh.closed_issues` (set) | `fake_github.closed_prs` (list) | set→list |
| `fake_gh.updated_bodies` | `fake_github.updated_pr_bodies` | Same shape |
| `fake_gh.get_issue(root, n)` | `fake_github.get_pr(root, n)` | IssueInfo→PRDetails |
| Comment IDs start at 1000 | Comment IDs start at 1000000 | Update hardcoded assertions |

### PRDetails helper pattern (local per file)

```python
def _make_pr_details(number: int, title: str, body: str) -> PRDetails:
    return PRDetails(
        number=number, url=f"https://github.com/test/repo/pull/{number}",
        title=title, body=body, state="OPEN", is_draft=True,
        base_ref_name="main", head_ref_name=f"plan-{number}",
        is_cross_repository=False, mergeable="UNKNOWN",
        merge_state_status="UNKNOWN", owner="test-owner", repo="test-repo",
    )
```

## Files to Migrate (36 total)

### Category A — Simple injection change (~15 files)

Tests whose production code only accesses `ctx.issues` (not `ctx.plan_backend`):

1. `tests/unit/cli/commands/exec/scripts/test_update_issue_body.py`
2. `tests/unit/cli/commands/exec/scripts/test_get_issue_body.py`
3. `tests/unit/cli/commands/exec/scripts/test_get_issue_timeline_prs.py`
4. `tests/unit/cli/commands/exec/scripts/test_get_plans_for_objective.py`
5. `tests/unit/cli/commands/exec/scripts/test_create_plan_from_context.py`
6. `tests/unit/cli/commands/exec/scripts/test_migrate_objective_schema.py`
7. `tests/unit/cli/commands/exec/scripts/test_store_tripwire_candidates.py`
8. `tests/unit/cli/commands/exec/scripts/test_update_objective_node.py`
9. `tests/unit/cli/commands/objective/test_check_cmd.py`
10. `tests/unit/cli/commands/exec/scripts/test_objective_save_to_issue.py`
11. `tests/unit/cli/commands/exec/scripts/test_objective_post_action_comment.py`
12. `tests/unit/cli/commands/exec/scripts/test_reply_to_discussion_comment.py`
13. `tests/unit/cli/commands/exec/scripts/test_pr_discussion_comments.py`
14. `tests/unit/cli/commands/exec/scripts/test_plan_save_to_issue.py` *(will be deleted in node 3.3)*
15. `tests/unit/cli/commands/exec/scripts/test_set_local_review_marker.py`

### Category B — Data seeding + assertion changes (~21 files)

Tests whose production code uses `require_plan_backend(ctx)`:

1. `tests/unit/cli/commands/exec/scripts/test_close_issue_with_comment.py`
2. `tests/unit/cli/commands/exec/scripts/test_get_plan_metadata.py`
3. `tests/unit/cli/commands/exec/scripts/test_mark_impl_started_ended.py`
4. `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`
5. `tests/unit/cli/commands/exec/scripts/test_post_workflow_started_comment.py`
6. `tests/unit/cli/commands/exec/scripts/test_register_one_shot_plan.py` *(hybrid — uses both require_issues AND require_plan_backend)*
7. `tests/unit/cli/commands/exec/scripts/test_upload_session.py`
8. `tests/unit/cli/commands/exec/scripts/test_trigger_async_learn.py`
9. `tests/unit/cli/commands/exec/scripts/test_update_plan_header.py`
10. `tests/unit/cli/commands/exec/scripts/test_get_plan_info.py`
11. `tests/unit/cli/commands/exec/scripts/test_create_impl_context_from_plan.py`
12. `tests/unit/cli/commands/exec/scripts/test_get_learn_sessions.py`
13. `tests/unit/cli/commands/exec/scripts/test_add_plan_label.py`
14. `tests/unit/cli/commands/exec/scripts/test_objective_apply_landed_update.py`
15. `tests/unit/cli/commands/exec/scripts/test_objective_fetch_context.py`
16. `tests/unit/cli/commands/exec/scripts/test_track_learn_evaluation.py`
17. `tests/unit/cli/commands/exec/scripts/test_handle_no_changes.py`
18. `tests/unit/cli/commands/exec/scripts/test_get_pr_for_plan.py`
19. `tests/unit/cli/commands/exec/scripts/test_plan_update_from_feedback.py`
20. `tests/unit/cli/commands/exec/scripts/test_plan_update_issue.py`
21. `tests/unit/cli/commands/exec/scripts/test_track_learn_result.py`

### Infrastructure cleanup (1 file)

- `packages/erk-shared/src/erk_shared/context/testing.py` — Remove `elif issues_explicitly_passed:` branch (lines 188-193) that auto-creates GitHubPlanStore. After this, `github_issues=` parameter only affects which issues gateway is composed into FakeGitHub, never affects plan_store.

## Implementation Sequence

1. **Category A files** — Mechanical find-and-replace, low risk
2. **Category B files** — Read each file, convert IssueInfo→PRDetails data seeding, update assertions. Each file needs individual attention to understand what plan_backend methods are called and what assertions exist.
3. **Infrastructure cleanup** — Remove dead branch in `context_for_test()`
4. **Verify** — Run full test suite

## Key Reference Files

| File | Purpose |
|---|---|
| `packages/erk-shared/src/erk_shared/context/testing.py` | `context_for_test()` with `issues_explicitly_passed` branch |
| `packages/erk-shared/src/erk_shared/gateway/github/fake.py` | FakeGitHub: `pr_comments`, `closed_prs`, `updated_pr_bodies`, `pr_details` |
| `packages/erk-shared/src/erk_shared/plan_store/planned_pr.py` | PlannedPRBackend method implementations |
| `packages/erk-shared/src/erk_shared/gateway/github/types.py:107` | PRDetails dataclass definition |
| `tests/test_utils/plan_helpers.py` | Existing `_plan_to_pr_details()` pattern for reference |
| `packages/erk-shared/src/erk_shared/context/helpers.py` | `require_plan_backend()`, `require_issues()` |

## Verification

```bash
# Run all affected tests
uv run pytest tests/unit/cli/commands/exec/scripts/ tests/unit/cli/commands/objective/ -x

# Run full fast-ci
make fast-ci
```
