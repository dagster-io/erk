---
title: Objective Commands
read_when:
  - "working with erk objective commands"
  - "implementing objective check or close functionality"
  - "understanding objective validation patterns"
last_audited: "2026-02-08"
audit_result: clean
tripwires:
  - action: "displaying user-provided text in Rich CLI tables without escaping"
    warning: "Use `escape_markup(value)` for user data in Rich tables. Brackets like `[text]` are interpreted as style tags and will disappear."
---

# Objective Commands

## Why Reconcile and Next-Plan Are Nearly Identical

<!-- Source: src/erk/cli/commands/objective/next_plan_cmd.py, next_plan -->

The `erk objective reconcile` and `erk objective next-plan` commands perform the same task — launching Claude to create an implementation plan from an objective step — but differ in their validation discipline:

**reconcile** enforces LBYL validation before launching Claude. It checks that the objective exists and has the `erk-objective` label, failing fast if validation fails. This prevents cryptic errors from launching Claude with invalid input.

**next-plan** skips validation and immediately launches Claude. This is useful when you trust the input or want to handle errors interactively within Claude rather than at the CLI boundary.

Both commands force plan mode by calling `ia_config.with_overrides(permission_mode_override="plan")` regardless of the user's config file setting. This ensures the agent explores and plans rather than immediately executing.

## Permission Mode Override Pattern

<!-- Source: packages/erk-shared/src/erk_shared/context/types.py, InteractiveAgentConfig.with_overrides -->

The `with_overrides()` method on `InteractiveAgentConfig` allows selective override of config values:

- Pass a value (e.g., `"plan"`) to force that mode
- Pass `None` to preserve the config file value

This pattern appears in both `reconcile` and `next-plan` commands. Both force `permission_mode_override="plan"` but differ in handling the `--dangerous` flag:

- **reconcile** always passes `allow_dangerous_override=None`, preserving the config file value
- **next-plan** conditionally overrides based on the `--dangerous` flag, allowing users to opt into skipping permission prompts

## Why next-plan Takes Optional Argument, reconcile Takes Required

<!-- Source: src/erk/cli/commands/objective/next_plan_cmd.py, next_plan -->

The `next-plan` command accepts an optional `ISSUE_REF` string argument. This flexibility allows the slash command `/erk:objective-next-plan` to prompt for the issue interactively if needed.

The `reconcile` command requires an integer `OBJECTIVE` argument because it performs upfront validation that needs the issue number immediately. The validation (checking `issue_exists()` and verifying the `erk-objective` label) happens before launching Claude, so the issue number can't be deferred.

## Validation Check Design

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->

The `validate_objective()` function returns a discriminated union — either `ObjectiveValidationSuccess` or `ObjectiveValidationError`. This allows callers to distinguish between "couldn't validate" (network error, issue not found) and "validation completed but found problems" (orphaned statuses, inconsistent numbering).

The success case includes `passed: bool` to indicate whether checks passed, plus detailed `checks: list[tuple[bool, str]]` for each validation rule. This structure supports both human-readable output (CLI) and structured JSON output (programmatic use with `--json-output`).

**Why both a passed field AND a checks list**: The `passed` field is the overall result (false if any check failed). The `checks` list provides granular detail about which specific rules failed and why. JSON consumers can filter or reprocess the list; human output can show a summary.

## Status/PR Consistency Rules

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->

The validation enforces semantic coupling between step status and PR reference:

- Steps with `pr: "#123"` (PR reference) should have `status: "done"` (or `"skipped"`)
- Steps with `pr: "plan #123"` (plan reference) should have `status: "in_progress"` (or `"skipped"`)
- Steps with `status: "done"` must have a PR reference (no orphaned done statuses)

**Why this matters**: The objective roadmap is the coordination document for multi-PR work. If statuses and PR references drift, future agents can't trust the roadmap to understand what's actually complete. The validation catches drift early, before it becomes a source of confusion.

## Phase Numbering Validation

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->

Phases are validated for sequential ordering by `(number, suffix)` tuples. This allows sub-phases like `1A, 1B, 1C` followed by `2` without triggering an error, but catches cases like `[1, 3, 2]` or `[1A, 1C, 1B]`.

**Why tuples instead of string comparison**: String comparison would treat `"10"` as less than `"2"` (lexicographic ordering). Tuple comparison handles numeric ordering correctly: `(1, "A") < (1, "B") < (2, "")`.

## Rich Markup Escaping in Tables

<!-- Source: src/erk/cli/commands/objective/list_cmd.py, list_objectives -->

User-provided objective titles may contain brackets like `[foo]`, which Rich interprets as style tags. The `list_objectives` command currently **does not escape** user data, which means titles with brackets will render incorrectly (the bracketed text disappears).

The correct pattern is:

```python
from rich.markup import escape as escape_markup

table.add_row(
    f"[link={issue.url}]#{issue.number}[/link]",
    escape_markup(issue.title),  # ← Escape user data
    format_relative_time(issue.created_at.isoformat()),
    issue.url,
)
```

**Why this is a tripwire**: It's a silent bug. The code doesn't crash; the output just looks wrong. And it's intermittent — only affects titles with brackets, which are rare enough to escape notice during development.

See [CLI Output Styling Guide](output-styling.md#rich-markup-escaping-in-cli-tables) for the full escaping pattern.

## Close Command Confirmation Pattern

<!-- Source: src/erk/cli/commands/objective/close_cmd.py, close_objective -->

The `close` command prompts for confirmation unless `--force` is provided. The confirmation pattern uses `ctx.console.confirm()` with `default=True`, meaning the user can press Enter to proceed.

**Why default to true**: Closing an objective is usually intentional and reversible (GitHub issues can be reopened). Defaulting to "yes" reduces friction while still providing a safety check for accidental invocations.

## Command Aliases

<!-- Source: src/erk/cli/commands/objective/__init__.py -->

All objective commands use the `register_with_aliases()` pattern, which registers both the full command name and a short alias:

| Command     | Alias | Why This Alias                                   |
| ----------- | ----- | ------------------------------------------------ |
| `check`     | `ch`  | Prefix of "check", avoids collision with "close" |
| `close`     | `c`   | First letter, unambiguous (check uses "ch")      |
| `list`      | `ls`  | Unix convention (ls for list)                    |
| `next-plan` | `np`  | First letters of both words                      |
| `reconcile` | `rec` | Prefix, unambiguous (r alone would be ambiguous) |

**Why aliases matter**: Objective commands are used in rapid iteration workflows. Typing `erk objective np` is faster than `erk objective next-plan`, reducing friction without sacrificing discoverability (the full name remains canonical).

## Related Documentation

- [CLI Output Styling Guide](output-styling.md) - Rich table formatting and markup escaping
- [LBYL Gateway Pattern](../architecture/lbyl-gateway-pattern.md) - Look-before-you-leap validation discipline
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - Gateway interface patterns including `issue_exists()`
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) - Result type patterns used by `validate_objective()`
