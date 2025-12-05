---
title: PR Commands
read_when:
  - "working with pull request commands"
  - "validating PR standards"
  - "using erk pr check command"
---

# PR Commands

This document describes the `erk pr` subcommands for working with pull requests.

## erk pr check

Validates that the current branch's PR meets project standards.

### Usage

```bash
erk pr check
```

### Validations Performed

1. **Issue Closing Reference**: When `.impl/issue.json` exists, verifies PR body contains `Closes #N` (case-insensitive)
2. **Checkout Footer**: Verifies PR body contains `erk pr checkout {pr_number}`

### Output

```
Checking PR #123 for branch feature-xyz...

[PASS] PR body contains issue closing reference (Closes #456)
[PASS] PR body contains checkout footer

All checks passed
```

### Integration

This command is automatically called by:

- `/gt:pr-submit` - After PR creation
- `/gt:pr-update` - After PR update
- `/git:pr-push` - After PR creation
- `/erk:plan-implement` - After PR creation (for worker-impl flows)

### Exit Codes

- `0` - All checks passed
- `1` - One or more checks failed

### Design Principles

**Non-blocking validation**: The command reports validation failures but does not prevent workflow continuation. This allows agents and users to make informed decisions about whether to address issues immediately or continue with their workflow.

**Context-aware checks**: Validation rules adapt based on the presence of `.impl/issue.json`. The issue closing reference check only runs when the PR is associated with a tracked issue.

## Related Topics

- [Command Organization](command-organization.md) - How commands are structured in the erk CLI
- [Output Styling](output-styling.md) - Formatting conventions for CLI output
- [Script Mode](script-mode.md) - Machine-readable output format
