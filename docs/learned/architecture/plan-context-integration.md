---
title: Plan Context Integration
read_when:
  - "using PlanContextProvider for PR generation"
  - "extracting plan content from branches"
  - "understanding how PR descriptions get plan context"
tripwires:
  - action: "using PlanContextProvider"
    warning: "Read this doc first. PlanContextProvider returns None on any failure (graceful degradation). Always handle the None case."
---

# Plan Context Integration

The `PlanContextProvider` extracts plan content for branches linked to erk-plan issues, enabling more accurate PR descriptions that understand the "why" behind changes.

## 5-Step Extraction Algorithm

Given a branch name, the provider attempts to extract plan context through these steps:

```
1. Extract issue number from branch name
   P5763-fix-bug → 5763
   ↓
2. Fetch the issue body from GitHub
   GET /repos/{owner}/{repo}/issues/5763
   ↓
3. Extract plan_comment_id from issue metadata
   Parse YAML header for `plan_comment_id: 123456789`
   ↓
4. Fetch the comment and extract plan content
   GET /repos/{owner}/{repo}/issues/comments/123456789
   ↓
5. Optionally get objective title if linked
   Parse `objective_issue: 100` → fetch title
```

If any step fails, the provider returns `None` (graceful degradation).

## Branch Naming Convention

The provider extracts issue numbers from branch names using these patterns:

| Pattern                | Extracted Issue |
| ---------------------- | --------------- |
| `P5763-fix-bug`        | 5763            |
| `5763-fix-bug`         | 5763            |
| `feature/P5763-update` | 5763            |
| `fix-bug`              | None            |

The leading `P` prefix is optional. The issue number must appear at the start of the branch name (after any path segments like `feature/`).

## Graceful Degradation

The provider is designed to fail silently and return `None` when:

- Branch doesn't match naming convention
- Issue doesn't exist
- Issue isn't an erk-plan issue (no `plan_comment_id`)
- Plan comment was deleted
- API errors occur

This allows callers to proceed without plan context:

```python
context = provider.get_plan_context(repo_root=repo_root, branch_name=branch)
if context is not None:
    # Use plan content for enhanced PR description
    include_plan_summary(context.plan_content)
else:
    # Fall back to commit messages only
    use_commit_messages_only()
```

## PlanContext Data Structure

When extraction succeeds, the provider returns:

```python
@dataclass(frozen=True)
class PlanContext:
    issue_number: int       # The erk-plan issue number
    plan_content: str       # Full plan markdown
    objective_summary: str | None  # "Objective #123: Title" if linked
```

## Usage in PR Generation

The `CommitMessageGenerator` uses `PlanContextProvider` to add plan context to PR descriptions. The priority order for context is:

1. **Plan Context** (highest) - Full understanding of intent
2. **Objective Summary** - Parent goal context
3. **Commit Messages** (lowest) - Technical changes only

## Reference Implementation

See `src/erk/core/plan_context_provider.py` for the canonical implementation.

## Related Topics

- [Plan Lifecycle](../planning/lifecycle.md) - How plans are created and stored
- [Commit Message Generation](../pr-operations/commit-message-generation.md) - Using plan context in PRs
