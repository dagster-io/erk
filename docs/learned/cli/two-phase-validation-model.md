---
title: Two-Phase Validation Model
read_when:
  - "implementing commands with user confirmations"
  - "designing commands that perform destructive mutations"
  - "adding confirmation prompts to CLI commands"
  - "deciding where to place confirmation logic in a command"
tripwires:
  - action: "implementing a command with user confirmations interleaved between mutations"
    warning: "Use two-phase model: gather ALL confirmations first (Phase 1), then perform mutations (Phase 2). Interleaving confirmations with mutations causes partial state on decline."
last_audited: "2026-02-08"
audit_result: regenerated
---

# Two-Phase Validation Model

Any CLI command that combines user confirmations with destructive mutations must batch all confirmations before any mutations begin. This document explains the foundational pattern — for the full pipeline architecture that scales this to complex commands, see [Linear Pipelines](../architecture/linear-pipelines.md).

## The Partial Mutation Problem

When confirmations are interleaved with mutations, a user declining any prompt leaves the system in an inconsistent state:

1. Command merges a PR (mutation)
2. Command asks "Delete the worktree?" (confirmation)
3. User says no
4. PR is merged but worktree remains — orphaned state

There is no undo for step 1. The user never consented to a "merge but keep worktree" outcome — they wanted either "merge and clean up" or "don't merge at all."

**The fix is structural**: separate the command into two phases with a hard boundary between them.

## Phase 1: Validation (Read-Only)

- Check all preconditions (PR state, branch existence, clean working tree)
- Narrow types from discriminated unions (see [EnsureIdeal Pattern](ensure-ideal-pattern.md))
- Gather **every** user confirmation into stored results
- Zero mutations — if anything fails or the user declines, the system is unchanged

## Phase 2: Execution (No Interaction)

- Perform mutations using pre-gathered confirmation results
- Never prompt the user — all decisions were made in Phase 1
- Short-circuit on first error (mutations already underway may not be reversible)

## Confirmation Capture Pattern

Confirmations gathered in Phase 1 must survive into Phase 2. The pattern is a frozen dataclass that captures the user's response:

<!-- Source: src/erk/cli/commands/land_cmd.py, CleanupConfirmation -->

See `CleanupConfirmation` in `src/erk/cli/commands/land_cmd.py` — a frozen dataclass with a single `proceed: bool` field. This result is stored in the command's state object and read during execution without re-prompting.

**Why a dataclass instead of a bare `bool`?** Named types make the confirmation's purpose explicit. When a command has multiple confirmations (e.g., "delete worktree?" and "update objective?"), distinct types prevent mix-ups. A bare `bool` named `cleanup_confirmed` is less clear than `CleanupConfirmation(proceed=True)`.

## When Confirmation Can Be Skipped

Three cases legitimately bypass the confirmation prompt while still using the two-phase structure:

| Case                           | Why                                       | Implementation                                                                         |
| ------------------------------ | ----------------------------------------- | -------------------------------------------------------------------------------------- |
| `--force` flag                 | User explicitly opts out of confirmations | Return `CleanupConfirmation(proceed=True)` immediately                                 |
| `--dry-run` mode               | No mutations will occur                   | Return `CleanupConfirmation(proceed=True)` — execution phase checks dry-run separately |
| Non-interactive mode (scripts) | No stdin to read from                     | Honor the confirmation's default value via `ScriptConsole`                             |

<!-- Source: src/erk/cli/commands/land_cmd.py, _gather_cleanup_confirmation -->

See `_gather_cleanup_confirmation()` in `src/erk/cli/commands/land_cmd.py` for how force, dry-run, and cleanup type interact to decide whether to prompt.

## Decision: When to Use This Pattern

**Use two-phase when ANY of these apply:**

- Command has 1+ confirmation prompts AND 1+ mutations
- Mutations cannot be rolled back (PR merges, branch deletions, issue updates)
- Users could reasonably decline a prompt after an earlier mutation

**Don't use two-phase when:**

- Command has no confirmations (pure mutations with `--force` or read-only operations)
- All mutations are idempotent and independently safe
- The command is a single atomic operation (one prompt, one mutation)

## Anti-Pattern: Inline Confirmation

```python
# WRONG: Confirmation between mutations
ctx.github.merge_pr(repo_root, pr_number)  # Mutation 1
if ctx.console.confirm("Delete worktree?"):  # Prompt AFTER mutation
    delete_worktree(worktree_path)           # Mutation 2
```

If the user declines, the PR is merged but the worktree survives. Neither the user nor the codebase expected this hybrid state.

```python
# CORRECT: All confirmations first, then all mutations
cleanup = _gather_cleanup_confirmation(ctx, ...)  # Phase 1
ctx.github.merge_pr(repo_root, pr_number)         # Phase 2
if cleanup.proceed:
    delete_worktree(worktree_path)
```

## Scaling: From Pattern to Pipeline

For simple commands (1-2 confirmations, 2-3 mutations), inline two-phase structure is sufficient. As commands grow in complexity, the pattern evolves:

1. **Inline two-phase** — Gather confirmations in a helper, execute mutations after. Suitable for ≤3 steps.
2. **Pipeline architecture** — Formal validation and execution pipelines with uniform step signatures and immutable state threading. Required when a command has 5+ steps, multiple error types, or needs a serialization boundary.

The land command evolved from inline two-phase to the full pipeline architecture. For the pipeline pattern, see:

- [Linear Pipelines](../architecture/linear-pipelines.md) — Validation/execution pipeline architecture
- [CLI-to-Pipeline Boundary](../architecture/cli-to-pipeline-boundary.md) — When to extract pipelines from CLI commands
- [Land State Threading](../architecture/land-state-threading.md) — Immutable state management across pipeline steps

## Related Documentation

- [EnsureIdeal Pattern](ensure-ideal-pattern.md) — Type narrowing in the validation phase
- [CI-Aware Commands](ci-aware-commands.md) — Commands must handle non-interactive mode
- [Output Styling Guide](output-styling.md) — Using `ctx.console.confirm()` for testable prompts
