---
title: Branch Naming Conventions
read_when:
  - "creating branches programmatically"
  - "implementing plan workflows"
  - "working with Graphite (gt) integration"
  - "debugging branch creation or naming issues"
  - "implementing automated branch creation"
---

# Branch Naming Conventions

## Overview

Erk uses **Graphite-style branch naming** for automated branch creation from plans and objectives. This convention enables integration with plan tracking, GitHub issues, and stack management.

## Standard Format

```
P{issue}-{description}-{date}-{time}
```

### Components

- **P{issue}**: Plan or issue number prefix (e.g., `P6547`)
- **{description}**: Slugified description from issue title
- **{date}**: Date in `MM-DD` format
- **{time}**: Time in `HHMM` format

### Example

Issue #6547: "Optimize objective-update-with-landed-pr command"

Branch name: `P6547-optimize-objective-update-02-01-0847`

**Breakdown:**

- `P6547` - Issue number
- `optimize-objective-update` - Slugified title (truncated)
- `02-01` - February 1st
- `0847` - 8:47 AM

## Slugification Rules

### Title to Branch Name

1. **Lowercase**: Convert entire title to lowercase
2. **Replace spaces**: Replace spaces with hyphens
3. **Remove special characters**: Keep only alphanumeric and hyphens
4. **Truncate if needed**: Keep reasonable length (~40 chars for description part)

### Examples

| Issue Title                                | Slugified Description           |
| ------------------------------------------ | ------------------------------- |
| "Optimize objective-update-with-landed-pr" | `optimize-objective-update`     |
| "Add TUI Support for Dashboard"            | `add-tui-support-for-dashboard` |
| "Fix: Bug in PR Sync"                      | `fix-bug-in-pr-sync`            |
| "Update docs (session analysis)"           | `update-docs-session-analysis`  |

## Implementation

### Python Code

```python
import re
from datetime import datetime

def slugify_title(title: str, max_length: int = 40) -> str:
    """Convert issue title to branch-safe slug."""
    # Lowercase and replace spaces with hyphens
    slug = title.lower().replace(" ", "-")

    # Remove special characters (keep alphanumeric and hyphens)
    slug = re.sub(r"[^a-z0-9-]", "", slug)

    # Remove consecutive hyphens
    slug = re.sub(r"-+", "-", slug)

    # Strip leading/trailing hyphens
    slug = slug.strip("-")

    # Truncate to max length
    if len(slug) > max_length:
        slug = slug[:max_length].rstrip("-")

    return slug

def generate_branch_name(issue_number: int, title: str) -> str:
    """Generate Graphite-style branch name."""
    description = slugify_title(title)
    now = datetime.now()
    date_str = now.strftime("%m-%d")
    time_str = now.strftime("%H%M")

    return f"P{issue_number}-{description}-{date_str}-{time_str}"
```

### Usage in Workflows

**Plan implementation:**

```bash
# Fetch issue data
issue_data=$(gh issue view 6547 --json number,title)
issue_number=$(echo "$issue_data" | jq -r '.number')
title=$(echo "$issue_data" | jq -r '.title')

# Generate branch name
branch_name=$(python -c "from erk.utils import generate_branch_name; print(generate_branch_name($issue_number, '$title'))")

# Create branch
gt create "$branch_name"
```

## When to Use

### ✅ Use Graphite-Style Naming

- **Automated plan workflows** - Issue-based branch creation
- **Objective tracking** - Links branch to objective/plan
- **GitHub integration** - Issue number enables auto-linking
- **Stack management** - Clear hierarchy and relationships

### ❌ Don't Use for Manual Branches

- **Quick fixes** - Manual `fix-typo` is fine
- **Experiments** - No need for issue tracking
- **One-off changes** - Overhead not justified

## Benefits

### Issue Tracking

- Branch name contains issue number → easy PR linking
- GitHub auto-links PR to issue
- Clear traceability from issue → branch → PR

### Timeline Information

- Date/time suffix shows when work started
- Useful for debugging stale branches
- Helps with branch cleanup decisions

### Stack Clarity

- Graphite recognizes pattern
- Clear parent-child relationships
- Easier navigation in stack views

## Troubleshooting

### Branch Already Exists

If timestamp collision occurs (rare, but possible in automated workflows):

```bash
# Append random suffix
branch_name="${branch_name}-$(openssl rand -hex 2)"
```

### Title Too Long

Slugification truncates at 40 chars by default. Adjust if needed:

```python
description = slugify_title(title, max_length=50)
```

### Special Characters

Slugification removes all special chars. If title is mostly special chars:

```python
if len(description) < 5:
    description = f"issue-{issue_number}"
```

## Real-World Examples

### Example 1: Plan Implementation

**Issue**: #6540 "Optimize objective update workflow"
**Created**: February 1, 2026, 8:30 AM
**Branch**: `P6540-optimize-objective-update-02-01-0830`

### Example 2: Documentation Plan

**Issue**: #6547 "Document Haiku delegation pattern"
**Created**: February 1, 2026, 8:47 AM
**Branch**: `P6547-document-haiku-delegation-02-01-0847`

### Example 3: Long Title Truncation

**Issue**: #1234 "Implement comprehensive multi-step workflow orchestration with error handling"
**Created**: February 1, 2026, 9:00 AM
**Branch**: `P1234-implement-comprehensive-multi-step-w-02-01-0900`
(Description truncated at 40 chars)

## Related Patterns

- [Plan Implementation Workflow](../planning/plan-implementation.md) - Where branch naming is used
- [Graphite Stack Management](../erk/graphite-stack-management.md) - Stack conventions
- [GitHub Integration](../integrations/github-integration.md) - Issue linking
