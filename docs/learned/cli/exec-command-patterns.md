---
title: Exec Command Patterns
read_when:
  - "writing new erk exec scripts"
  - "generating PR or issue body content"
  - "creating diagnostic messages in workflows"
tripwires:
  - action: "writing PR/issue body generation in exec scripts"
    warning: "Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability."
---

# Exec Command Patterns

Established patterns for implementing erk exec scripts with consistent, testable behavior.

## PR/Issue Body Generation

When exec scripts create or update PR bodies or issue comments with diagnostic information, use helper functions for consistency and testability.

### Pattern: Diagnostic PR Body

**Purpose:** Generate a PR body that explains error scenarios to users, with clear structure and actionable guidance.

**Implementation approach:**

1. Create a helper function `_build_pr_body()` that takes scenario parameters
2. Return a formatted markdown string
3. Include these sections in order:
   - Status indicator (heading or emoji)
   - Link to originating plan issue
   - Detection reason with timestamp
   - Relevant context (commits, branches, etc.)
   - User guidance for next steps

**Key structure elements:**

```markdown
## Status: [Scenario Name]

[Brief explanation of what happened]

**Plan Issue:** [Link to plan]
**Detected:** [ISO timestamp]

### Why This Happened

[Explanation of root cause, e.g., recent commits or duplicate work]

### Recent Commits

[List of commits that may explain the scenario]

### What You Should Do

[Clear action items for the user]
```

**Benefits of helper function approach:**

- Consistent messaging across workflows
- Testable independently from workflow (unit tests)
- Reusable across multiple commands
- Easy to update messaging centrally

### Pattern: Issue Notification Comment

**Purpose:** Post a brief notification comment on the plan issue, summarizing what happened and where to find details.

**Implementation approach:**

1. Create a helper function `_build_issue_comment()`
2. Keep it concise (3-5 sentences)
3. Include:
   - Status indicator
   - Link to diagnostic PR
   - Brief explanation
   - Suggested user action

**Key structure elements:**

```markdown
**Status:** [Outcome]

Implementation produced [scenario]. See the [diagnostic PR](link) for details.

[One sentence of guidance]
```

**Benefits:**

- Users see update in their plan issue without leaving GitHub
- Complements the detailed PR body
- Cross-links PR and plan issue for context

## Testing Patterns

When testing PR/issue body generators:

### Unit Test Structure

```python
def test_build_pr_body_includes_plan_link():
    """PR body should link to originating plan issue."""
    body = _build_pr_body(plan_id=123, ...)
    assert "issues/123" in body or "#123" in body

def test_build_pr_body_includes_timestamp():
    """PR body should include detection timestamp."""
    body = _build_pr_body(...)
    assert len(body) > 0  # Should contain timestamp
    assert "Detected" in body or "detected" in body.lower()

def test_build_issue_comment_is_concise():
    """Issue comment should be brief and actionable."""
    comment = _build_issue_comment(...)
    lines = comment.strip().split('\n')
    assert len(lines) <= 10  # Guideline: 3-5 sentences max
```

### Testing Approach

1. **Format validation**: Verify markdown structure (links, headings)
2. **Content presence**: Check for required information (links, timestamps)
3. **User clarity**: Ensure action items are explicit
4. **Length**: Verify brevity (especially for comments)

## Label Coordination

When exec scripts apply labels, coordinate with central label definitions.

### Pattern: Label Definition and Application

1. **Define centrally:** Add label to the central label definitions registry
2. **Apply via gateway:** Use GitHub gateway methods to apply labels
3. **Document meaning:** Add to relevant docs explaining when label is applied

### Example Flow

**Definition (in plan_issues.py):**

Labels are defined in a central registry with name, color, and description.

**Application (in exec script):**

Use the GitHub gateway to apply labels to PRs:

```python
github.add_labels_to_pr(pr_number, ["label-name"])
```

**Documentation:**

Document the label meaning and usage in relevant docs. For example, the `no-changes` label is documented in [No-Code-Changes Handling](../planning/no-changes-handling.md).

## Helper Function Guidelines

### When to Create Helper Functions

Create helper functions when:

- The same formatting logic is used in multiple places
- The function is testable independently
- The function encapsulates a reusable pattern
- The function improves readability and maintainability

### Helper Function Naming

- Prefix with `_` to indicate internal use: `_build_pr_body()`
- Use clear verb + noun: `_format_timestamps()`, `_collect_commits()`
- Avoid generic names: use `_build_diagnostic_message()` not `_build_message()`

### Helper Function Structure

```python
def _build_pr_body(
    plan_id: int,
    detection_reason: str,
    recent_commits: list[str],
    run_url: str,
) -> str:
    """Build diagnostic PR body explaining error scenario.

    Args:
        plan_id: Issue number of originating plan
        detection_reason: Human-readable reason for scenario
        recent_commits: List of commit hashes or messages
        run_url: GitHub Actions run URL

    Returns:
        Formatted markdown string for PR body
    """
    # Implementation
    return body
```

**Key patterns:**

- Use type hints for clarity
- Include docstring with purpose and arguments
- Return formatted string, don't mutate state
- Keep function pure (no side effects)

## Related Topics

- [No-Code-Changes Handling](../planning/no-changes-handling.md) — Understanding the scenario these patterns support
- [erk exec Commands](erk-exec-commands.md) — Command reference including handle-no-changes
