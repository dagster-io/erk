---
read_when:
- considering invoke_without_command=True for Click command groups
- deciding between command groups vs separate commands for local/remote workflows
- understanding why erk uses separate commands instead of unified groups
title: Local/Remote Command Group Pattern (Deprecated)
tripwires:
- action: using this pattern
  warning: 'BEFORE: Using invoke_without_command=True to unify local/remote variants
    → READ: Why this pattern was abandoned'
---

# Local/Remote Command Group Pattern (Deprecated)

**Historical pattern for unified local/remote command execution in Click. No longer used in erk.**

## Why This Pattern Was Abandoned

Click's `invoke_without_command=True` allows a group to execute when called directly (local) while offering subcommands (remote). This seems elegant but created operational friction:

**The fundamental problem:** Local and remote execution have different preconditions, options, and error modes. Unifying them under one command name obscured these differences.

### Concrete Issues

1. **Help text ambiguity** — Users running `erk pr address --help` saw both local and remote documentation mixed together, making it unclear which flags applied to which mode

2. **Option validation complexity** — The group function needed conditional logic to validate options based on whether a subcommand was invoked (`ctx.invoked_subcommand is None`), spreading validation across multiple functions

3. **Discoverability** — Remote execution via `erk pr address remote` was non-obvious compared to the explicit `erk launch pr-address` pattern

4. **Maintenance burden** — Each new local/remote pair required implementing the group pattern, subcommand registration, and context checking

## Current Architecture: Separate Commands + Unified Launch

<!-- Source: src/erk/cli/commands/pr/address_cmd.py, address() -->
<!-- Source: src/erk/cli/commands/pr/fix_conflicts_cmd.py, fix_conflicts() -->
<!-- Source: src/erk/cli/commands/launch_cmd.py, launch() -->

Erk now uses **separate commands** for clearer separation of concerns:

- **Local execution:** Simple `@click.command()` functions (e.g., `erk pr address`)
- **Remote execution:** Unified `erk launch <workflow-name>` command that dispatches to GitHub Actions

See `address()` in `src/erk/cli/commands/pr/address_cmd.py` for the local command structure, and `launch()` in `src/erk/cli/commands/launch_cmd.py` for remote workflow triggering.

### Benefits of Separation

**Clarity:** Each command has focused documentation and options specific to its execution mode

**Validation:** Each command validates its own preconditions without conditional context checking

**Discoverability:** `erk launch --help` shows all available remote workflows in one place

**Simplicity:** No group ceremony — just commands that do one thing

## The One Remaining Use: `erk init`

<!-- Source: src/erk/cli/commands/init/__init__.py, init_group() -->

The only current use of `invoke_without_command=True` is `erk init`, which runs full initialization by default but offers `erk init capability` subcommands for managing optional features.

This works because:

- **Shared context:** Both the group and subcommands operate on erk initialization
- **Progressive disclosure:** The default action (full init) is the 99% case; subcommands are for advanced users
- **Consistent options:** Flags like `--force` apply to the same initialization logic

See `init_group()` in `src/erk/cli/commands/init/__init__.py` for implementation.

## Decision Framework

Use `invoke_without_command=True` when:

- The group's default action and its subcommands share **the same domain and preconditions**
- You want **progressive disclosure** (simple default + advanced subcommands)
- Options on the group apply to **both** the default action and subcommands

Avoid it when:

- Default action and subcommands have **different preconditions** (e.g., local vs remote)
- Execution modes diverge in **error handling or validation**
- You're creating **parallel workflows** rather than progressive disclosure

## Related Patterns

**For local/remote workflows:** See [Workflow Commands](workflow-commands.md) for the current `erk launch` architecture

**For command organization:** See [Command Organization](command-organization.md) for when to use groups vs top-level commands

**For Click help formatting:** See `ErkCommandGroup` in `src/erk/cli/help_formatter.py` for custom help organization (separate from `invoke_without_command` pattern)
