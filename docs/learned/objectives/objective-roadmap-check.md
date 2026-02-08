---
title: Objective Check Command — Semantic Validation
read_when:
  - "validating objective roadmap consistency beyond structure"
  - "understanding why check command exists separate from parsing"
  - "adding new validation checks to objective check"
tripwires:
  - action: "manually parsing objective roadmap markdown"
    warning: "Use `erk objective check`. It handles structural parsing, status inference, and semantic validation."
  - action: "adding structural validation to check_cmd.py"
    warning: "Structural validation (phase headers, table format) belongs in objective_roadmap_shared.py. check_cmd.py handles semantic validation only."
  - action: "raising exceptions from validate_objective()"
    warning: "validate_objective() returns discriminated unions, never raises. Only CLI presentation functions (_output_json, _output_human) raise SystemExit."
---

# Objective Check Command — Semantic Validation

## Why Semantic Validation Is Separate from Parsing

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->
<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py, parse_roadmap -->

The roadmap parser in `objective_roadmap_shared.py` handles **structural** validation: can the markdown be parsed into phases and steps? The check command's `validate_objective()` in `check_cmd.py` adds a **semantic** layer: is the parsed roadmap internally consistent?

This separation exists because structural parsing is shared across consumers — both `erk objective check` and `erk exec update-roadmap-step` call `parse_roadmap()`. Semantic checks only make sense for read-only validation. Mixing them would force every mutation command to validate consistency before operating, coupling mutation to validation rules and adding unnecessary overhead.

## Two-Layer Validation Architecture

| Layer      | Responsibility                                         | Consumers      | When it runs                 |
| ---------- | ------------------------------------------------------ | -------------- | ---------------------------- |
| Structural | Phase headers exist, tables parse, rows have 4 columns | check + update | Every `parse_roadmap()` call |
| Semantic   | Label present, status/PR consistency, phase ordering   | check only     | `erk objective check`        |

## Why Each Semantic Check Exists

| Check                 | Why it matters                                                                                                      |
| --------------------- | ------------------------------------------------------------------------------------------------------------------- |
| `erk-objective` label | Prevents running check on plan issues or random issues that happen to contain markdown tables                       |
| Roadmap parses        | Early exit — no point running semantic checks on unparseable content                                                |
| Status/PR consistency | Catches stale status after manual table edits (someone adds a PR reference but forgets to update the Status column) |
| No orphaned done      | Catches typos where someone marks a step done but forgets to add the PR number                                      |
| Sequential phases     | Catches copy-paste errors (duplicate phase numbers, out-of-order phases)                                            |

The status/PR consistency check is particularly important because the [two-tier status system](roadmap-status-system.md) allows both explicit and inferred status. When a human manually edits a table, they can create contradictions that the parser silently accepts — for example, a step with PR `#123` but explicit status `pending`. The parser respects the explicit status (by design), but the check command flags the contradiction.

## Discriminated Union Result Pattern

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, ObjectiveValidationResult -->

The `ObjectiveValidationResult` type alias in `check_cmd.py` is a discriminated union of `ObjectiveValidationSuccess | ObjectiveValidationError`. This distinction captures a three-state outcome that exceptions can't cleanly model:

1. **Validation couldn't run** (`ObjectiveValidationError`) — issue not found, API failure
2. **Validation ran and passed** (`ObjectiveValidationSuccess` with `passed=True`)
3. **Validation ran and found problems** (`ObjectiveValidationSuccess` with `passed=False`)

This matters because callers need different responses for "issue doesn't exist" vs "issue exists but has problems." Only the CLI presentation layer (`_output_json`, `_output_human`) converts results to exit codes and `SystemExit` — the core `validate_objective()` function is designed for programmatic use and never raises.

## Command Evolution

The original `erk exec objective-roadmap-check` exec script defaulted to JSON output. When it was promoted to `erk objective check` as a proper Click subcommand, the default switched to human-readable `[PASS]/[FAIL]` output, with JSON available via `--json-output`. This matches the convention that CLI commands default to human output and require explicit flags for machine-readable formats.

## Anti-Patterns

**WRONG: Adding structural validation to check_cmd.py.**
Structural checks (missing table headers, malformed separator lines) belong in the shared parser so all consumers — `check`, `update-roadmap-step`, and any future commands — benefit from them. Adding structural checks to `check_cmd.py` means the update command silently accepts structurally invalid content.

**WRONG: Raising exceptions from `validate_objective()`.**
The function returns result types, never raises. This enables programmatic callers to inspect results without catching exceptions, and keeps the decision of "what to do with failures" in the presentation layer where it belongs.

## Related Documentation

- [Roadmap Parser](roadmap-parser.md) — Shared parser, structural validation, and update command
- [Roadmap Status System](roadmap-status-system.md) — Two-tier status resolution that check validates against
- [Roadmap Validation Rules](roadmap-validation.md) — Complete validation rule inventory across all commands
