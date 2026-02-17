---
title: PreToolUse Hook Design Patterns
read_when:
  - "creating or modifying a PreToolUse hook"
  - "choosing between blocking (exit 2) and informational (exit 0) hooks"
  - "understanding capability-gated context injection"
tripwires:
  - action: "creating a PreToolUse hook"
    warning: "Broken hooks fail silently (exit 0, no output) — indistinguishable from correct no-fire behavior. Structure as pure functions + thin orchestrator. Read docs/learned/testing/hook-testing.md first."
  - action: "reproducing stdin JSON parsing or file detection logic in a new hook"
    warning: "Reuse the canonical pure functions in pre_tool_use_hook.py. Writing from scratch reintroduces edge cases already solved (empty stdin, missing keys, wrong types)."
last_audited: "2026-02-17 16:00 PT"
audit_result: clean
---

# PreToolUse Hook Design Patterns

PreToolUse hooks are erk's Tier 3 (just-in-time) context injection mechanism. This document captures the cross-cutting design decisions for building them — not the code itself, which lives in source.

## The Silent Failure Problem

Hooks that malfunction fail silently: they exit 0 with no output, and nobody notices the reminder is missing. Unlike a broken CLI command (which produces a visible error), a broken hook produces _nothing_ — indistinguishable from correct behavior when the hook shouldn't fire.

This silent failure mode drives every architectural decision below. It explains why hooks are more heavily decomposed than typical erk code of equivalent complexity: the cost of an undetected bug is invisible degradation of agent behavior.

## Pure Function Architecture

Because silent failures make bugs invisible, erk hooks decompose into three layers:

1. **Pure functions** — Each concern (stdin extraction, file detection, output building) is an independent function with no I/O. This enables exhaustive edge-case testing without mocking.
2. **Capability gate** — Checks whether the reminder feature is installed before injecting anything, enabling per-project opt-out.
3. **Thin orchestrator** — A small entry point that wires pure functions together with I/O. Its only job is sequencing.

<!-- Source: src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py, pre_tool_use_hook -->

See `pre_tool_use_hook()` in `src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py` for the canonical implementation.

**Why not just test the entry point end-to-end?** The entry point has a combinatorial explosion of failure modes (empty stdin × missing keys × wrong types × non-erk project × missing capability). Pure functions let you test each axis independently, then integration tests cover the wiring.

## Capability-Gating via state.toml

PreToolUse hooks don't unconditionally inject reminders. They first check whether the reminder capability is installed in `.erk/state.toml`. This indirection serves three purposes:

1. **Project-level control** — Not every erk-managed project wants every reminder. The state.toml flag acts as a per-project feature toggle.
2. **Graceful degradation** — If the state file is missing or malformed, the hook exits silently rather than crashing. This follows the fail-open pattern: informational hooks should never prevent work.
3. **Testability** — Tests install/uninstall capabilities by writing state.toml to `tmp_path`, avoiding monkeypatching.

<!-- Source: src/erk/core/capabilities/detection.py, is_reminder_installed -->

See `is_reminder_installed()` in `src/erk/core/capabilities/detection.py` for the detection logic.

## Exit Code Semantics

PreToolUse hooks use Claude Code's exit code protocol to control tool execution:

| Exit Code | Effect                                                   | When to use                                  |
| --------- | -------------------------------------------------------- | -------------------------------------------- |
| 0         | Proceed with tool execution; stdout is a system reminder | Informational hooks (coding standard nudges) |
| 2         | Block tool execution; stdout shown as error              | Safety gates (genuinely unsafe actions)      |
| Other     | Non-blocking error, logged but tool proceeds             | Should not occur in well-tested hooks        |

**Key design decision:** Erk's coding-standard hooks (dignified-python, fake-driven-testing) always exit 0. They are reminders, not gates. Blocking a Write because the agent _might_ violate a coding standard would be hostile — the reminder is sufficient, and the agent retains autonomy.

Exit code 2 is reserved for hooks where the tool's default behavior is actively unwanted (e.g., the ExitPlanMode hook blocks plan approval when a plan was already saved to GitHub).

## File Detection: Inclusion and Exclusion

The Python file detection deliberately excludes `.pyi` stub files. Stub files define type signatures, not implementation logic, so coding standard reminders about LBYL patterns, frozen dataclasses, and no-default-parameters don't apply. This is an instance of a broader principle: **noisy reminders teach agents to ignore all reminders.** Every false positive erodes the signal value of legitimate reminders across the entire system.

## Decorator Ordering in hook_command

<!-- Source: src/erk/hooks/decorators.py, hook_command -->

Rather than stacking three decorators on every hook (getting the order wrong silently breaks logging), erk provides `hook_command()` in `src/erk/hooks/decorators.py`.

The critical architectural constraint: `logged_hook` must wrap the function _before_ `@click.pass_context` so that logging captures everything, including early exits from project-scope checks. If the ordering is reversed, crashes in the outer decorators go unlogged — another instance of the silent failure problem. The `hook_command` decorator encodes this ordering so individual hooks can't get it wrong.

## Anti-Patterns

**WRONG: Inline stdin parsing in the entry point**
Mixing JSON parsing, type checking, and business logic in the orchestrator makes edge cases untestable without full CliRunner setup. Extract each concern into a pure function.

**WRONG: Blocking (exit 2) for coding standard reminders**
Blocking prevents the agent from writing code at all. The agent may have good reasons to deviate from standards. Use exit 0 and let the reminder influence, not control.

**WRONG: Skipping capability checks**
A hook that fires unconditionally cannot be disabled per-project. Always gate on state.toml or an equivalent mechanism.

## Related Topics

- [Context Injection Architecture](../architecture/context-injection-tiers.md) — Where PreToolUse (Tier 3) fits in the three-tier system
- [Hooks Guide](hooks.md) — General hook lifecycle, matchers, and configuration
- [Hook Testing Patterns](../testing/hook-testing.md) — Pure function + integration testing strategy
