---
title: CLI Optional Arguments with Inference
read_when:
  - "making a CLI argument optional"
  - "inferring CLI arguments from context"
  - "branch-based argument defaults"
---

# CLI Optional Arguments with Inference

Pattern for making CLI arguments optional by inferring them from context.

## Pattern

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
```

## Inference Sources (Priority Order)

1. Explicit CLI argument
2. Branch name pattern (P{number}-...)
3. .impl/issue.json file
4. Error with helpful message

## Helper Function

Use `extract_leading_issue_number()` from `erk_shared.naming`:

```python
from erk_shared.naming import extract_leading_issue_number

branch = "P4655-erk-learn-command-01-11-0748"
issue_num = extract_leading_issue_number(branch)  # Returns 4655
```
