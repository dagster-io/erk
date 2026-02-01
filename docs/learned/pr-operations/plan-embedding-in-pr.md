---
title: Plan Embedding in PR Body
read_when:
  - "implementing PR body formatting with HTML"
  - "understanding how plans are embedded in PRs"
  - "debugging plan visibility in pull requests"
  - "working with <details> collapsible sections in PR bodies"
---

# Plan Embedding in PR Body

When submitting a PR from a plan implementation (`.impl/` folder), erk embeds the full plan content in the PR body using a collapsible `<details>` section. This provides reviewers with complete context without cluttering the PR description.

## Feature Overview

Plan embedding is implemented in `src/erk/cli/commands/pr/submit_pipeline.py:587-599` via `_build_plan_details_section()`. When a PR is submitted with plan context, the plan content is:

1. Wrapped in a `<details>` collapsible section
2. Tagged with the plan issue number in the summary
3. Appended to the PR body **after the checkout footer**
4. Never included in the git commit message

## Implementation Structure

### Two-Target Pattern

The implementation uses **two separate body strings**:

- `pr_body` - Plain text for git commit messages (no HTML)
- `pr_body_for_github` - Enhanced version with plan embedding (GitHub-specific HTML)

See [PR Body Formatting](../architecture/pr-body-formatting.md) for the architectural pattern.

### Function: `_build_plan_details_section()`

```python
def _build_plan_details_section(plan_context: PlanContext) -> str:
    """Build a collapsed <details> section embedding the plan in the PR body."""
    issue_num = plan_context.issue_number
    parts = [
        "",
        "## Implementation Plan",
        "",
        "<details>",
        f"<summary><strong>Implementation Plan</strong> (Issue #{issue_num})</summary>",
        "",
        plan_context.plan_content,
        "",
        "</details>",
    ]
    return "\n".join(parts)
```

**Location**: `src/erk/cli/commands/pr/submit_pipeline.py:587-601`

### Integration in `finalize_pr()`

```python
# Embed plan in PR body if available (not in commit message)
pr_body_for_github = pr_body
if state.plan_context is not None:
    pr_body_for_github = pr_body + _build_plan_details_section(state.plan_context)

# Build footer and combine
metadata_section = build_pr_body_footer(
    pr_number=state.pr_number,
    issue_number=issue_number,
    plans_repo=effective_plans_repo,
)
final_body = pr_body_for_github + metadata_section
```

**Location**: `src/erk/cli/commands/pr/submit_pipeline.py:635-646`

The two-target body pattern is clearly visible here:

- `pr_body` - Plain text used for git commit messages (no HTML plan embedding)
- `pr_body_for_github` - Enhanced with plan embedding for GitHub PR body only

This ensures that plan content appears in the GitHub UI for reviewers but never pollutes the git commit history. The test at `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py:291-294` verifies this separation.

## HTML Structure

The generated HTML follows this pattern:

```html
## Implementation Plan

<details>
  <summary><strong>Implementation Plan</strong> (Issue #1234)</summary>

  # Plan Title Plan content here...
</details>
```

### Critical Placement

The `<details>` block is appended **after** the user-provided description but **before** the checkout footer. This ordering is safe because:

1. The checkout footer validator only checks that the footer appears at the end
2. HTML tags between the description and footer don't interfere with validation
3. The footer metadata remains parseable

### Issue Number in Summary

The summary line includes `(Issue #{issue_num})` to provide:

- **Bidirectional navigation**: Quick link from PR to plan issue
- **Context**: Immediate visibility of which plan this PR implements
- **Traceability**: Clear relationship between PR and planning artifact

## Example from Tests

From `tests/unit/cli/commands/pr/submit_pipeline/test_finalize_pr.py:249-293`:

```python
def test_embeds_plan_in_pr_body(tmp_path: Path) -> None:
    """Plan context embedded in PR body but NOT in commit message."""
    plan_content = "# My Plan\n\nSome implementation details"
    plan_ctx = PlanContext(
        issue_number=1234,
        plan_content=plan_content,
        objective_summary=None,
    )

    # ... setup ...

    result = finalize_pr(ctx, state)

    # Verify PR body contains the plan details block
    assert "<details>" in updated_body
    assert "<summary><strong>Implementation Plan</strong> (Issue #1234)</summary>" in updated_body
    assert plan_content in updated_body
    assert "</details>" in updated_body

    # Verify commit message does NOT contain plan details block
    assert "<details>" not in commit_msg
    assert plan_content not in commit_msg
```

## Key Invariants

1. **HTML only in PR body**: The `<details>` block never appears in git commit messages
2. **Safe placement**: `<details>` blocks are placed after the checkout footer, passing validation
3. **Conditional embedding**: Plan content only embedded when `state.plan_context is not None`
4. **Immutable plan content**: The embedded plan is read-only markdown text, not editable

## Related Documentation

- [PR Body Formatting](../architecture/pr-body-formatting.md) - Two-target pattern explanation
- [PR Submit Phases](pr-submit-phases.md) - Phase 6 integration details
- [Plan Implementation Workflow](../planning/workflow.md) - When plan context is available
