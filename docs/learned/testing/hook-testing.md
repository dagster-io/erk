---
title: Hook Testing Patterns
read_when:
  - "writing tests for any hook (PreToolUse, UserPromptSubmit, ExitPlanMode)"
  - "creating a new hook implementation"
  - "testing hooks that read from stdin or check capabilities"
tripwires:
  - action: "creating or modifying a hook"
    warning: "Hooks fail silently (exit 0, no output) — untested hooks are invisible failures. Read docs/learned/testing/hook-testing.md first."
  - action: "using monkeypatch or unittest.mock in hook tests"
    warning: "Use ErkContext.for_test() with CliRunner instead of mocking. See docs/learned/testing/hook-testing.md."
last_audited: "2026-02-08 00:00 PT"
audit_result: clean
---

# Hook Testing Patterns

## Why Hook Testing Requires a Different Mindset

Hooks default to silent success: exit 0, no output. When a hook malfunctions — wrong key in JSON, missing capability check, unhandled None — there is no runtime error signal. The hook simply does nothing. This makes negative tests (verifying silence under wrong conditions) more valuable than positive tests, because a broken hook looks identical to a correctly-silent hook.

This silent-failure property drives every architectural decision below.

## The Two-Layer Architecture

All erk hooks follow the same structural pattern: pure functions for logic, a thin orchestration entry point for I/O. This isn't arbitrary — it exists because hook logic is complex (nested JSON parsing, capability checks, marker file state machines) but the I/O surface is tiny (stdin read, click.echo, file existence checks). Separating them means:

- **Pure functions** test at Layer 3 (unit) with zero dependencies — no tmp_path, no CliRunner, no mocking. These cover the combinatorial edge cases that would be painful to set up through the full pipeline.
- **Integration entry point** tests at Layer 4 with CliRunner and `ErkContext.for_test()`. These verify the orchestration wiring — that the right pure functions are called in the right order with the right I/O.

<!-- Source: src/erk/cli/commands/exec/scripts/pre_tool_use_hook.py, extract_file_path_from_stdin -->
<!-- Source: src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py, determine_exit_action -->
<!-- Source: src/erk/cli/commands/exec/scripts/user_prompt_hook.py, build_session_context -->

The pure/integration split is used consistently across all five hook implementations: `pre_tool_use_hook`, `exit_plan_mode_hook`, `user_prompt_hook`, `session_id_injector_hook`, and `tripwires_reminder_hook`. See any test file in `tests/unit/cli/commands/exec/scripts/test_*_hook.py` for the pattern.

## Pure Function Testing: What to Cover

The critical insight is that stdin JSON extraction functions must handle every level of the nested structure defensively (LBYL). The edge case matrix:

| Input condition                                        | Expected behavior | Why it matters                                     |
| ------------------------------------------------------ | ----------------- | -------------------------------------------------- |
| Empty string / whitespace                              | Return None       | Hooks receive empty stdin in edge cases            |
| Valid JSON, missing expected key                       | Return None       | `tool_input` may not be present for all tool types |
| Key exists but wrong type (string where dict expected) | Return None       | Claude's tool_input shape varies by tool           |
| Key exists but empty string                            | Return None       | Empty file_path is semantically absent             |

**Detection functions** (e.g., file extension checks) must test the similar-but-wrong case — `.pyi` is not `.py`, even though both are Python-related. This catches suffix-matching bugs.

**Output builder functions** should assert on required keywords, not exact strings. Output text changes frequently; the invariant is which concepts appear, not the exact wording.

## Integration Testing: The Five Scenarios

Every hook integration test suite should cover these five scenarios. They map to the silent-failure paths in the `@hook_command` decorator's orchestration:

| Scenario                | Setup                                              | Expected               | Why                                        |
| ----------------------- | -------------------------------------------------- | ---------------------- | ------------------------------------------ |
| **Positive**            | All conditions met                                 | Output present, exit 0 | Validates the happy path works end-to-end  |
| **Wrong trigger**       | Condition not met (e.g., .js file for Python hook) | Empty output, exit 0   | Hook must be selective                     |
| **Missing capability**  | No state.toml or capability not installed          | Silent, exit 0         | Hooks must degrade gracefully              |
| **Outside erk project** | No `.erk/` directory in tmp_path                   | Silent, exit 0         | Hooks fire in all projects via Claude Code |
| **Missing stdin data**  | Required key absent from stdin JSON                | Silent, exit 0         | Partial stdin is a real production case    |

<!-- Source: src/erk/hooks/decorators.py, HookContext -->

The `HookContext.is_erk_project` flag (derived from `.erk/` directory existence) is the universal gate — every hook checks it first. Integration tests create or omit `(tmp_path / ".erk").mkdir()` to control this.

## Capability Setup

Hooks that depend on installed capabilities read from `state.toml` in the `.erk/` directory. In tests, write this file using `tomli_w.dump()` with the capability flags needed. The structure is `{"reminders": {"installed": ["capability-name"]}}`.

<!-- Source: src/erk/core/capabilities/detection.py, is_reminder_installed -->

See `_setup_dignified_python_reminder()` in the pre_tool_use_hook tests or `_setup_reminders()` in the user_prompt_hook tests for working examples. Both follow the same pattern: create `tmp_path / ".erk" / "state.toml"` with the desired capability list.

## Stdin JSON Format

PreToolUse hooks receive this structure on stdin:

```json
{
  "session_id": "...",
  "tool_name": "Write",
  "tool_input": {
    "file_path": "/path/to/file",
    "content": "..."
  }
}
```

UserPromptSubmit hooks receive `{"session_id": "..."}`. ExitPlanMode hooks also receive `{"session_id": "..."}`. Fields in `tool_input` vary by tool — always use LBYL to check each nesting level before accessing.

## Common Mistakes

- **Testing only the happy path**: Silent failure is the default mode, so the five negative scenarios above are where bugs hide. A hook that always returns nothing passes the positive test trivially.
- **Using monkeypatch instead of ErkContext**: `ErkContext.for_test(repo_root=tmp_path, cwd=tmp_path)` with CliRunner is the standard pattern. Monkeypatching `Path.home()` or environment variables creates fragile tests that break when internals change.
- **Forgetting the `.erk/` directory**: Without `(tmp_path / ".erk").mkdir()`, `HookContext.is_erk_project` is False and the hook exits silently — making the test pass for the wrong reason.
- **Using `context_for_test()` when `ErkContext.for_test()` suffices**: The `context_for_test()` factory from `erk_shared.context.testing` is needed only when injecting fakes (FakeGit, FakeClaudeInstallation). For hooks that don't need gateway fakes, `ErkContext.for_test()` is simpler and sufficient.
