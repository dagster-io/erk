---
name: erk-planning
description: >
  This skill should be used when creating or managing erk-plan issues. Use when working with
  GitHub issues that store implementation plans (create, update, get, implement). Covers the
  plan issue structure, commands section, and plan content update workflow.
---

# Erk Planning Skill

## Overview

Erk-plan issues store implementation plans in GitHub with structured metadata. This skill covers
creating, reading, and updating plan issues.

## Plan Issue Structure (Schema v2)

Erk-plan issues have a two-part structure:

1. **Issue Body**: Contains metadata in a `plan-header` block
2. **First Comment**: Contains the actual plan content in a `plan-body` block

### Why Two Parts?

- Issue body contains small, structured metadata (~1KB)
- Plan content can be large (10KB+) and goes in comment
- The `plan_comment_id` in metadata enables direct lookup of plan content

## Creating Plan Issues

Use `create_plan_issue()` from `erk_shared.github.plan_issues`:

```python
from erk_shared.github.plan_issues import create_plan_issue

result = create_plan_issue(
    github_issues=github,
    repo_root=repo_root,
    plan_content="# My Plan\n\n- Step 1\n- Step 2",
    title=None,  # Extracted from H1 heading
    plan_type=None,  # Or "extraction" for extraction plans
    extra_labels=None,  # Additional labels beyond erk-plan
)

if result.success:
    print(f"Created issue #{result.issue_number}: {result.issue_url}")
```

The function:

1. Extracts title from H1 heading (or uses provided title)
2. Creates erk-plan label if needed
3. Creates issue with metadata-only body
4. Adds first comment with plan content
5. Updates issue body with `plan_comment_id` for direct lookup
6. Adds Commands section (for standard plans, not extraction plans)

## Updating Plan Content

Use `update_plan_issue_content()` to update plan content in an existing issue:

```python
from erk_shared.github.plan_issues import update_plan_issue_content

result = update_plan_issue_content(
    github_issues=github,
    repo_root=repo_root,
    issue_number=42,
    new_plan_content="# Updated Plan\n\n- New step 1\n- New step 2",
)

if result.success:
    print(f"Updated comment #{result.comment_id}")
else:
    print(f"Error: {result.error}")
```

### CLI Command

Update via CLI using `erk exec plan-update-issue`:

```bash
# From file
erk exec plan-update-issue --issue 42 --plan-file plan.md

# From session (looks up plan by slug)
erk exec plan-update-issue --issue 42 --session-id <session-id>

# From stdin
cat plan.md | erk exec plan-update-issue --issue 42
```

## Plan Metadata (plan-header)

The issue body contains a `plan-header` metadata block:

```yaml
# plan-header
schema_version: "2"
created_at: "2025-01-01T00:00:00Z"
created_by: "username"
plan_comment_id: 1234567890 # Direct lookup for plan content
# ... other optional fields
```

Key fields:

- `schema_version`: Always '2' for current format
- `plan_comment_id`: GitHub comment ID containing plan content
- `created_at`, `created_by`: Creation metadata
- `worktree_name`: Set when implementation worktree is created

## Reading Plan Content

To read plan content from an issue:

```python
from erk_shared.github.metadata import extract_plan_header_comment_id

# Get plan_comment_id from issue body
comment_id = extract_plan_header_comment_id(issue.body)

if comment_id is not None:
    # Fetch the specific comment
    plan_body = github.get_comment_by_id(repo_root, comment_id)
```

## Commands Section

Standard plans (not extraction plans) include a Commands section in the issue body:

```markdown
## Commands

Implement this plan:

- Interactive: `erk implement 42`
- Non-interactive: `erk implement 42 --dangerous`

Submit to remote:

- `erk plan submit 42`
```

The Commands section is added automatically by `create_plan_issue()` after the plan is created.

## Error Handling

Both `create_plan_issue()` and `update_plan_issue_content()` return result objects
that never raise exceptions. Check `result.success` and `result.error`:

```python
result = update_plan_issue_content(...)

if not result.success:
    if result.comment_id is not None:
        # Partial failure - we know which comment but update failed
        print(f"Failed to update comment #{result.comment_id}: {result.error}")
    else:
        # Complete failure - issue not found or missing plan_comment_id
        print(f"Error: {result.error}")
```

## Related Documentation

- `docs/learned/architecture/erk-architecture.md` - Dependency injection patterns
- `fake-driven-testing` skill - Testing with FakeGitHubIssues
