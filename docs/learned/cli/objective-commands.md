---
title: Objective Commands
read_when:
  - "working with erk objective commands"
  - "implementing objective check or close functionality"
  - "understanding objective validation patterns"
last_audited: "2026-02-05"
audit_result: edited
tripwires:
  - action: "displaying user-provided text in Rich CLI tables without escaping"
    warning: "Use `escape_markup(value)` for user data in Rich tables. Brackets like `[text]` are interpreted as style tags and will disappear."
---

# Objective Commands

The `erk objective` command group manages erk objectives - high-level goals that track multiple related plans.

## Command Overview

| Command                   | Alias | Description                                      |
| ------------------------- | ----- | ------------------------------------------------ |
| `erk objective check`     | `ch`  | Validate an objective's format and roadmap       |
| `erk objective close`     | `c`   | Close an objective GitHub issue                  |
| `erk objective list`      | `ls`  | List open objectives                             |
| `erk objective next-plan` | `np`  | Launch Claude to create plan from objective step |
| `erk objective reconcile` | `rec` | Validate and launch Claude for objective step    |

All commands are registered via `register_with_aliases()` in `src/erk/cli/commands/objective/__init__.py`.

## Next-Plan Command

The `erk objective next-plan` command launches Claude in plan mode to create an implementation plan from an objective step.

### Key Behavior

1. **Resolves config**: Loads `InteractiveAgentConfig` from `[interactive-agent]` in `~/.erk/config.toml`
2. **Forces plan mode**: Calls `ia_config.with_overrides(permission_mode_override="plan")` to ensure plan mode regardless of config
3. **Launches Claude**: Calls `ctx.agent_launcher.launch_interactive()` with the `/erk:objective-next-plan` slash command
4. **Supports `--dangerous` flag**: Passes `--allow-dangerously-skip-permissions` to Claude when set

See `next_plan_cmd.py` for implementation, `InteractiveAgentConfig.with_overrides()` in `erk_shared/context/types.py` for the override pattern.

### Permission Override Pattern

The `with_overrides()` method on `InteractiveAgentConfig` conditionally overrides config values:

- Setting to a value (like `"plan"`) forces that mode
- Setting to `None` preserves the config file value

This pattern is reused by both `next-plan` and `reconcile` commands.

### Related Slash Command

After launching, Claude executes `/erk:objective-next-plan` (file: `.claude/commands/erk/objective-next-plan.md`), which:

1. Fetches the objective issue
2. Analyzes the roadmap
3. Guides the user through planning an implementation for a step
4. Saves the plan to a GitHub issue

## Reconcile Command

The `erk objective reconcile` command validates an objective and launches Claude to create a plan for its next step. It is functionally similar to `next-plan` but adds LBYL validation.

### Key Differences from Next-Plan

- **Required argument**: Takes a required `OBJECTIVE` integer (issue number), not optional
- **LBYL validation**: Checks `issue_exists()` and verifies `erk-objective` label before launching
- **No `--dangerous` flag**: Always launches with default permissions

### Validation (LBYL Pattern)

The command performs Look Before You Leap validation before launching Claude:

1. **Check existence**: `ctx.github.issues.issue_exists(repo.root, objective)` before fetching
2. **Check labels**: Verify `erk-objective` label exists on the issue
3. **Fail early**: Exit with clear error message if validation fails

This pattern prevents cryptic errors from launching Claude with an invalid objective. See `reconcile_cmd.py` for implementation.

## Check Command

The `erk objective check` command validates an objective's format and roadmap consistency without launching Claude.

### Validation Checks

1. Issue has `erk-objective` label
2. Roadmap parses successfully
3. Status/PR consistency (done steps should have PR references)
4. No orphaned done statuses
5. Phase numbering is sequential

Supports `--json-output` for structured output. See `check_cmd.py` and the `validate_objective()` function for implementation.

## Close Command

The `erk objective close` command closes an objective GitHub issue after validation (must have `erk-objective` label, must be open). Prompts for confirmation unless `--force` is provided. See `close_cmd.py` for implementation.

## Rich Markup Escaping

When displaying user-provided titles in Rich tables, bracket sequences like `[text]` are interpreted as Rich style tags. Always escape user data with `escape_markup()` from `rich.markup`. See [CLI Output Styling Guide](output-styling.md#rich-markup-escaping-in-cli-tables) for complete details.

## Related Documentation

- [CLI Output Styling Guide](output-styling.md) - Table formatting and Rich escaping
- [LBYL Gateway Pattern](../architecture/lbyl-gateway-pattern.md) - Existence checking pattern
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - `issue_exists()` method
