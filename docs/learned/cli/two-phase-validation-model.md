---
title: Two-Phase Validation Model for Complex Commands
read_when:
  - "implementing commands with multiple confirmations"
  - "designing commands that perform destructive mutations"
  - "working on erk land or similar multi-step commands"
tripwires:
  - action: "implementing a command with multiple user confirmations"
    warning: "Use two-phase model: gather ALL confirmations first (Phase 1), then perform mutations (Phase 2). Inline confirmations cause partial state on decline."
---

# Two-Phase Validation Model

Complex CLI commands that perform multiple mutations should use a two-phase model.

## Phase 1: Validation

- Gather ALL user confirmations upfront
- Perform all precondition checks
- NO mutations occur in this phase
- Collect all decisions into confirmation objects

## Phase 2: Execution

- Perform mutations in sequence
- Use pre-gathered confirmations
- No user interaction in this phase

## Why This Matters

Partial mutations are dangerous. If a command:

1. Merges a PR
2. Asks for confirmation to delete worktree
3. User says no

The PR is already merged but the worktree remains - an inconsistent state.

## Implementation Pattern

Create frozen dataclasses to capture confirmation results:

```python
@dataclass(frozen=True)
class CleanupConfirmation:
    """Pre-gathered cleanup confirmation result.

    Captures user's response to cleanup prompt during validation phase,
    allowing all confirmations to be batched upfront before any mutations.
    """

    proceed: bool  # True = proceed with cleanup, False = preserve
```

Gather confirmations during validation, then thread them through to execution:

1. Validation phase calls `_gather_cleanup_confirmation()` - prompts user
2. Result stored in context object (`cleanup_confirmed` field)
3. Execution phase uses stored result - no additional prompts

## Reference Implementation

See `CleanupConfirmation` and `_gather_cleanup_confirmation()` in `src/erk/cli/commands/land_cmd.py`.

Key functions:

- `_gather_cleanup_confirmation()`: Prompts during validation
- `_cleanup_and_navigate()`: Uses pre-gathered confirmation during execution

## Related Topics

- [CI-Aware Commands](ci-aware-commands.md) - Commands must skip prompts in CI
- [Output Styling Guide](output-styling.md) - Using `ctx.console.confirm()` for testability
