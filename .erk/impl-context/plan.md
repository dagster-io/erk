# Fix: Objective Roadmap Rendering and Validation Sync

## Context

When creating objective #8950, two bugs caused the `erk objective check` validation to fail on every newly-created objective:

1. `objective-render-roadmap` hardcodes all nodes as `pending` with no PR, ignoring status/pr fields in the input JSON
2. `format_objective_content_comment()` wraps raw markdown (with descriptions, test sections) between roadmap-table markers, but the validator re-renders from YAML using `render_roadmap_tables()` which produces a stripped-down format (headers + tables only, with PR count suffix). These never match.

## Bug 1: `objective-render-roadmap` ignores status/pr

**File:** `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py`

**Lines 168-184** hardcode `pending` and `None`:
```python
sections.append(f"| {step_id} | {step_desc} | pending | - |")
# ...
RoadmapNode(id=step_id, description=step_desc, status="pending", pr=None, ...)
```

**Fix:** Read status/pr from input:
```python
status = step_data.get("status", "pending")
pr = step_data.get("pr")
pr_display = pr if pr is not None else "-"
# Use status and pr_display in table row
# Use status and pr in RoadmapNode constructor
```

Also handle the `depends_on` variant (line 170).

**Test:** `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py` — add test case with pre-set status/pr fields.

## Bug 2: Comment tables don't match validator format at creation time

**File:** `packages/erk-shared/src/erk_shared/gateway/github/metadata/core.py:793-809`

`format_objective_content_comment()` wraps raw content with markers via `wrap_roadmap_tables_with_markers()`. This captures descriptions and test sections between markers. The validator's `rerender_comment_roadmap()` replaces the marker-bounded section with `render_roadmap_tables()` output (headers + tables only, PR count suffix). Mismatch on first check.

**Fix:** After creating the comment body, normalize the roadmap table section to canonical format. In `format_objective_content_comment()`:

1. After `wrap_roadmap_tables_with_markers()`, extract the YAML from the content (it's embedded in the same markdown at this point)
2. Parse with `parse_roadmap_frontmatter()`, group with `group_nodes_by_phase()`, enrich with `enrich_phase_names()`
3. Render canonical tables with `render_roadmap_tables()`
4. Replace the marker-bounded section with the canonical rendering

This ensures the comment is created in the same format the validator expects.

**Alternative (simpler):** After `create_objective_issue()` creates the issue body and comment, call `rerender_comment_roadmap(issue_body, comment_body)` and update the comment. This is already done in the update path — we'd just add it to the create path. This approach is at line 224-226 in `plan_issues.py`. After `add_comment`, fetch the issue body, rerender, and update the comment.

**Preferred approach:** The simpler alternative — add a normalization step in `create_objective_issue()` after the comment is created (around line 237). After updating the issue body with `objective_comment_id`, also rerender and update the comment:

```python
# Step 7b: Normalize roadmap tables in comment to canonical format
rerendered = rerender_comment_roadmap(updated_body, objective_comment)
if rerendered is not None and rerendered != objective_comment:
    github_issues.update_comment(repo_root, comment_id, rerendered)
```

This requires `update_comment` to exist on `GitHubIssues` (check if it does, add if not).

## Files to modify

1. `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py` — read status/pr from input
2. `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py` — test with pre-set status/pr
3. `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py` — add normalization step after comment creation
4. Potentially `packages/erk-shared/src/erk_shared/gateway/github/issues/abc.py` — add `update_comment` if missing

## Test Coverage Goals

These bugs slipped through because:
1. Bug 1: `test_objective_render_roadmap.py` never passed a step with `status`/`pr` fields and asserted they appeared in the output — a parametric gap.
2. Bug 2: `format_objective_content_comment()` and `rerender_comment_roadmap()` were each tested in isolation. No test joined them to verify the "producer/consumer contract" invariant.

**New tests to add:**

### Round-trip invariant test (Bug 2)
In `tests/unit/cli/commands/exec/scripts/test_objective_save_to_issue.py` (or a new file):

```python
def test_create_objective_comment_passes_validation(fake_github_issues):
    """Newly-created objective comment should already be in canonical format."""
    result = create_objective_issue(...)
    issue_body = fake_github_issues.get_issue_body(result.plan_number)
    comment_body = fake_github_issues.get_comment_body(...)
    rerendered = rerender_comment_roadmap(issue_body, comment_body)
    assert rerendered == comment_body  # Same check as erk objective check
```

This is the "generate → validate" roundtrip pattern. Any time there's a generate function and a validate function for the same artifact, they must have a shared test.

### Parametric status/pr test (Bug 1)
In `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py`:

```python
def test_render_roadmap_preserves_status_and_pr():
    """status and pr fields in input must appear in table rows and YAML output."""
    input_json = {"phases": [{"name": "Phase", "steps": [
        {"id": "1.1", "description": "Step", "status": "done", "pr": "#8841"}
    ]}]}
    result = runner.invoke(objective_render_roadmap, input=json.dumps(input_json))
    assert "| done | #8841 |" in result.output
    assert "status: done" in result.output
    assert "pr: '#8841'" in result.output
```

## Files to modify

1. `src/erk/cli/commands/exec/scripts/objective_render_roadmap.py` — read status/pr from input
2. `tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py` — add parametric status/pr test
3. `packages/erk-shared/src/erk_shared/gateway/github/plan_issues.py` — add normalization step after comment creation
4. `tests/unit/cli/commands/exec/scripts/test_objective_save_to_issue.py` — add round-trip invariant test

## Verification

1. Run `uv run pytest tests/unit/cli/commands/exec/scripts/test_objective_render_roadmap.py -v`
2. Run `uv run pytest tests/unit/cli/commands/exec/scripts/test_objective_save_to_issue.py -v`
3. Run `ty check` on modified files
4. Manual: create a test objective and verify `erk objective check` passes on first try without any manual fixup
