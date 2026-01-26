---
title: Cli Tripwires
read_when:
  - "working on cli code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from cli/*.md frontmatter -->

# Cli Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding user-interactive steps (confirmations, prompts) without CI detection** → Read [CI-Aware Commands](ci-aware-commands.md) first. Commands with user interaction must check `in_github_actions()` and skip prompts in CI. Interactive prompts hang indefinitely in GitHub Actions workflows.

**CRITICAL: Before displaying user-provided text in Rich CLI tables** → Read [CLI Output Styling Guide](output-styling.md) first. Use `escape_markup(value)` for user data. Brackets like `[text]` are interpreted as Rich style tags and will disappear.

**CRITICAL: Before displaying user-provided text in Rich CLI tables without escaping** → Read [Objective Commands](objective-commands.md) first. Use `escape_markup(value)` for user data in Rich tables. Brackets like `[text]` are interpreted as style tags and will disappear.

**CRITICAL: Before implementing a command with multiple user confirmations** → Read [Two-Phase Validation Model for Complex Commands](two-phase-validation-model.md) first. Use two-phase model: gather ALL confirmations first (Phase 1), then perform mutations (Phase 2). Inline confirmations cause partial state on decline.

**CRITICAL: Before putting checkout-specific helpers in navigation_helpers.py** → Read [Checkout Helpers Module](checkout-helpers.md) first. `src/erk/cli/commands/navigation_helpers.py` imports from `wt.create_cmd`, which creates a cycle if navigation_helpers tries to import from `wt` subpackage. Keep checkout-specific helpers in separate `checkout_helpers.py` module instead.

**CRITICAL: Before running any erk exec subcommand** → Read [erk exec Commands](erk-exec-commands.md) first. Check syntax with `erk exec <command> -h` first, or load erk-exec skill for workflow guidance.

**CRITICAL: Before using blocking operations (user confirmation, editor launch) in CI-executed code paths** → Read [CI-Aware Commands](ci-aware-commands.md) first. Check `in_github_actions()` before any blocking operation. CI has no terminal for user input.

**CRITICAL: Before using click.confirm() after user_output()** → Read [CLI Output Styling Guide](output-styling.md) first. Use ctx.console.confirm() for testability, or user_confirm() if no context available. Direct click.confirm() after user_output() causes buffering hangs because stderr isn't flushed.

**CRITICAL: Before using erk exec commands in scripts** → Read [erk exec Commands](erk-exec-commands.md) first. Some erk exec subcommands don't support `--format json`. Always check with `erk exec <command> -h` first.

**CRITICAL: Before writing PR/issue body generation in exec scripts** → Read [Exec Command Patterns](exec-command-patterns.md) first. Use `_build_pr_body` and `_build_issue_comment` patterns from handle_no_changes.py for consistency and testability.
