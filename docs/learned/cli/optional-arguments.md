---
title: CLI Optional Arguments with Inference
read_when:
  - "making a CLI argument optional"
  - "inferring CLI arguments from context"
  - "implementing branch-based argument defaults"
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# CLI Optional Arguments with Inference

Pattern for making CLI arguments optional by inferring them from context when not provided.

## Pattern Overview

When a CLI command needs a value that can be inferred from context (branch name, .impl/ folder, etc.), make the argument optional and implement inference fallback.

## Inference Priority Order

1. **Explicit CLI argument** - User-provided value takes precedence
2. **plan-ref.json** - Check `.impl/plan-ref.json` for plan ID
3. **.impl/issue.json file** - Check local implementation tracking (legacy)
4. **Error with helpful message** - Explain what was expected

## Implementation Pattern

<!-- Source: src/erk/cli/commands/pr/dispatch_cmd.py, dispatch_cmd -->

See the `dispatch_cmd()` function in `src/erk/cli/commands/pr/dispatch_cmd.py` or `check_cmd()` in `src/erk/cli/commands/pr/check_cmd.py` for concrete examples of this pattern. The key sequence is: check for an explicit argument first, then fall back to `read_plan_ref()` on the `.impl/` directory, then raise a `ClickException` if neither source provides a value.

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
- [Activation Scripts](activation-scripts.md) - Shell integration for commands
