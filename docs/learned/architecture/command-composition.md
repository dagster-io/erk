---
title: Command Composition Pattern
read_when:
  - "creating an exec script that orchestrates other exec scripts"
  - "understanding setup-impl command architecture"
  - "adding CWD injection for testability"
tripwires:
  - action: "using Path.cwd() directly in an exec script without CWD injection"
    warning: "Use `cwd: Path | None = None` parameter defaulting to `Path.cwd()` for testability. This allows tests to override the working directory."
    score: 5
---

# Command Composition Pattern

Exec scripts can orchestrate other exec scripts as sub-commands, aggregating their JSON outputs into a combined result. This pattern enables complex workflows while keeping individual commands focused and testable.

## Pattern

```
Orchestrator exec script
  ├── Sub-command 1 (e.g., setup-impl-from-pr)
  ├── Sub-command 2 (e.g., impl-init)
  └── Sub-command 3 (e.g., cleanup-impl-context)
```

The orchestrator calls sub-commands as Python functions (not subprocess calls), aggregates their results, and returns a combined JSON output.

## Example: `setup-impl`

The `setup-impl` command (`src/erk/cli/commands/exec/scripts/setup_impl.py`) demonstrates this pattern:

1. **Detects plan source** (issue, file, existing `.erk/impl-context/`, or branch name)
2. **Delegates** to `setup_impl_from_pr` for the heavy lifting
3. **Validates** by running `impl-init`
4. **Cleans up** `.erk/impl-context/` staging directory

Each sub-command returns its own result, and the orchestrator combines them into a single JSON response.

## CWD Injection for Testability

Exec scripts that use `Path.cwd()` should accept a `cwd` parameter:

<!-- Source: src/erk/cli/commands/exec/scripts/impl_init.py, _validate_impl_folder -->

See `_validate_impl_folder()` in `src/erk/cli/commands/exec/scripts/impl_init.py` for the canonical example: it accepts `cwd: Path | None = None` and defaults to `Path.cwd()` internally, allowing tests to override the working directory without monkey-patching or `os.chdir()`.

## JSON Output Aggregation

Orchestrator commands emit multiple JSON objects as they execute sub-commands. Each line is a complete JSON object. The calling agent parses them sequentially:

```json
{"success": true, "source": "issue", "pr_number": 123, "has_plan_tracking": true}
{"cleaned": true}
{"success": true, "source": "issue", "has_plan_tracking": true, "valid": true}
```

## Related Topics

- [erk exec Commands](../cli/erk-exec-commands.md) - Command reference
- [Inference Hoisting](inference-hoisting.md) - Why LLM calls stay in the skill layer
