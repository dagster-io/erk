---
title: erk pr summarize Command
read_when:
  - "generating PR descriptions for existing PRs"
  - "updating PR body with plan context"
  - "understanding pr summarize vs pr submit"
---

# erk pr summarize Command

Generates a PR description (title and body) for an existing PR by incorporating plan context from linked erk-plan issues.

## Usage

```bash
erk pr summarize [PR_NUMBER]
```

**Arguments:**

- `PR_NUMBER` (optional): The PR number to summarize. If omitted, uses the PR for the current branch.

## When to Use

Use `pr summarize` when you need to:

- **Update an existing PR's description** after changes
- **Regenerate PR body with plan context** after linking a plan
- **Fix PR descriptions** that were created without plan context

This command is distinct from `erk pr submit` which creates the PR and generates its description as part of submission.

## Plan Context Detection

The command automatically detects and incorporates plan context:

### With Plan Context

When a linked erk-plan issue is found:

```
   Incorporating plan from issue #6386
   Linked to [objective] Improve PR operations feedback

[Generated PR description with plan context...]
```

**Styling:**

- Plan message: Green text (`fg="green"`)
- Objective message: Green text (when available)
- Blank line separator after feedback

### Without Plan Context

When no linked plan is found:

```
   No linked plan found

[Generated PR description from commit messages...]
```

**Styling:**

- Message: Dimmed text (`dim=True`)
- Blank line separator after feedback

## Context Priority

The command uses `CommitMessageGenerator` with identical context priority to `pr submit`:

1. **Plan context** (from linked erk-plan issue)
2. **Objective context** (from linked objective issue)
3. **Commit messages** (fallback when no plan/objective)

This ensures PR descriptions are consistent regardless of when they were generated.

## Output Pattern

```
Fetching PR details...
Checking for plan context...

   Incorporating plan from issue #6386
   Linked to [objective] Improve PR operations feedback

Generating PR description...

Title: Add plan context feedback to pr summarize command
Body:
[Generated description incorporating plan context]

Updated PR #1234 with new description.
```

## Relationship to Other Commands

- `erk pr submit` - Creates PR and generates description (uses same feedback pattern)
- `erk pr edit` - Manual PR editing (doesn't regenerate description)
- `erk plan submit` - Creates branch and PR with plan context

## Implementation Details

**Location:** `src/erk/cli/commands/pr/summarize_cmd.py:120-131`

**Plan Context Feedback Pattern:**

```python
if plan_context is not None:
    click.echo(
        click.style(
            f"   Incorporating plan from issue #{plan_context.issue_number}",
            fg="green",
        )
    )
    if plan_context.objective_summary is not None:
        click.echo(click.style(f"   Linked to {plan_context.objective_summary}", fg="green"))
else:
    click.echo(click.style("   No linked plan found", dim=True))
click.echo("")
```

**Styling Convention:**

This feedback pattern is standardized across plan-aware PR commands (`pr submit` and `pr summarize`). Future plan-aware commands should follow this convention for consistency.

## Related Documentation

- [PR Submit Phases](../../pr-operations/pr-submit-phases.md) - Workflow phases for pr submit
- [Commit Message Generation](../../pr-operations/commit-message-generation.md) - Context priority ordering
- [Output Styling](../output-styling.md) - Standardized plan context feedback pattern
- [Plan Context Integration](../../architecture/plan-context-integration.md) - How PlanContextProvider works
