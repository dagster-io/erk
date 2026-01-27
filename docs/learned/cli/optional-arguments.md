---
title: CLI Optional Arguments with Inference
read_when:
  - "making a CLI argument optional"
  - "inferring CLI arguments from context"
  - "implementing branch-based argument defaults"
---

# CLI Optional Arguments with Inference

Pattern for making CLI arguments optional by inferring them from context when not provided.

## Pattern Overview

When a CLI command needs a value that can be inferred from context (branch name, .impl/ folder, etc.), make the argument optional and implement inference fallback.

## Inference Priority Order

1. **Explicit CLI argument** - User-provided value takes precedence
2. **Branch name pattern** - Extract from `P{number}-...` branch naming
3. **.impl/issue.json file** - Check local implementation tracking
4. **Error with helpful message** - Explain what was expected

## Implementation Pattern

```python
@click.command("mycommand")
@click.argument("issue", type=str, required=False)
@click.pass_obj
def mycommand(ctx: ErkContext, issue: str | None) -> None:
    # Priority 1: Explicit argument
    if issue is not None:
        issue_number = _extract_issue_number(issue)
    else:
        # Priority 2: Infer from branch name (P123-...)
        branch = ctx.git.get_current_branch(ctx.cwd)
        issue_number = extract_leading_issue_number(branch)

        if issue_number is None:
            # Priority 3: Check .impl/issue.json
            impl_issue = ctx.cwd / ".impl" / "issue.json"
            if impl_issue.exists():
                data = json.loads(impl_issue.read_text())
                issue_number = data.get("issue_number")

        if issue_number is None:
            raise click.ClickException(
                "Could not infer issue number. "
                "Provide explicitly or run from a P{number}-... branch."
            )
```

## Helper Function

Use `extract_leading_issue_number()` from `erk_shared.naming`:

```python
from erk_shared.naming import extract_leading_issue_number

branch = "P4655-erk-learn-command-01-11-0748"
issue_num = extract_leading_issue_number(branch)  # Returns 4655

branch = "feature-branch"
issue_num = extract_leading_issue_number(branch)  # Returns None
```

## When to Use This Pattern

**Good candidates for optional arguments:**

- Issue numbers (inferable from branch name or .impl/)
- Repository identifiers (inferable from git remote)
- Project paths (inferable from current directory)

**Not good candidates:**

- Values that can't be reliably inferred
- Security-sensitive inputs
- Destructive operation confirmations

## Error Messages

When inference fails, provide actionable error messages:

```python
# GOOD: Tells user what to do
"Could not infer issue number. Provide explicitly or run from a P{number}-... branch."

# BAD: Doesn't help user
"Issue number required."
```

## Example Commands Using This Pattern

- `erk learn [ISSUE]` - Infers issue from branch name
- `erk land [BRANCH]` - Infers branch from current checkout

## Related Topics

- [Command Organization](command-organization.md) - Overall CLI structure
- [Script Mode](script-mode.md) - Shell integration for commands
