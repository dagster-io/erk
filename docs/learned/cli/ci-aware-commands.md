---
title: CI-Aware Commands
read_when:
  - "implementing commands that may run in GitHub Actions"
  - "adding user prompts or confirmations to workflow commands"
  - "debugging CI workflow hangs"
tripwires:
  - action: "adding user-interactive steps to command workflows"
    warning: "Check if running in CI mode first using $CI/$GITHUB_ACTIONS environment variables. Implement conditional branching (if CI then auto-proceed, else prompt). See learn command Step 5 pattern."
  - action: "calling blocking commands/tools in workflow orchestration"
    warning: "Verify all blocking operations have CI-aware branching. Commands assuming interactive execution will block in GitHub Actions."
---

# CI-Aware Commands

Commands that present findings, request confirmations, or interact with users must handle both execution contexts.

## The Problem

Commands with interactive elements will block indefinitely in CI environments because:

1. No human is available to respond to prompts
2. stdin may not be connected or available
3. GitHub Actions will time out waiting for input

This affects any command that has user interaction steps in the middle of a workflow orchestration.

## Detection Pattern

Check for CI mode using environment variables:

```bash
# Bash detection
if [ -n "$CI" ] || [ -n "$GITHUB_ACTIONS" ]; then
    echo "Running in CI mode"
else
    echo "Running in interactive mode"
fi
```

## Branching Pattern

Structure your command to branch based on execution context:

```
if CI_MODE:
    # Use sensible defaults, auto-proceed
    # Example: write all HIGH/MEDIUM priority items
else:
    # Prompt user for confirmation
    # Allow selection/filtering
```

## Reference Implementation

The `/erk:learn` command (Step 5 - Present Findings) demonstrates this pattern in `.claude/commands/erk/learn.md`:

- **CI Mode**: Auto-proceeds to write documentation for all HIGH/MEDIUM priority items
- **Interactive**: Prompts user to confirm which items to include

The command checks both `$CI` and `$GITHUB_ACTIONS` before determining behavior, ensuring compatibility across different CI systems.

## Environment Variables

| Variable          | Set By              | Purpose              |
| ----------------- | ------------------- | -------------------- |
| `$CI`             | Most CI systems     | General CI indicator |
| `$GITHUB_ACTIONS` | GitHub Actions only | GitHub-specific      |

Check both for maximum compatibility across CI platforms.

## Common Pitfalls

1. **Only checking `$GITHUB_ACTIONS`** - Other CI systems exist and may use `$CI` instead
2. **Forgetting stdin issues** - Even "safe" prompts may block if stdin isn't available
3. **No default behavior** - CI mode needs sensible automatic actions that don't require user input
4. **Inconsistent testing** - Test both CI and interactive modes to catch branching bugs

## Related Topics

- [Learn Workflow](../planning/learn-workflow.md) - Specific application to documentation generation
- [CLI Output Styling Guide](output-styling.md) - Best practices for user confirmations
- [Command Execution Strategies](../tui/command-execution.md) - Subprocess handling in different contexts
