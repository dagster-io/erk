---
title: FakePromptExecutor API Migration - Gateway to Core
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
tripwires:
  - action: "using output=, should_fail=, or transient_failures= parameters in FakePromptExecutor"
    warning: "These are the deleted gateway API. Use simulated_* parameters (tests/fakes/) or prompt_results/streaming_events (erk_shared/core/fakes.py). See migration table."
  - action: "importing FakePromptExecutor from erk_shared.gateway.prompt_executor.fake"
    warning: "This module was deleted in the consolidation. Import from tests.fakes.prompt_executor or erk_shared.core.fakes instead."
read_when:
  - "writing tests that use FakePromptExecutor"
  - "choosing between the two FakePromptExecutor implementations"
  - "encountering old-style output=/should_fail= patterns in test code"
---

# FakePromptExecutor API Migration: Gateway to Core

## Why This Migration Happened

PR #6587 consolidated two separate PromptExecutor abstractions into one:

1. **Gateway PromptExecutor** — single-shot prompts with simple `output`/`should_fail` constructor
2. **Core PromptExecutor** — full-featured with interactive, streaming, command, and prompt modes

The gateway version was deleted because it was a subset of the core's capabilities. The core ABC needed to support metadata extraction (PR URLs, issue numbers), event streaming (tool events, spinner updates), and hook interaction (zero-turns detection) — none of which the gateway's simple API could express.

## Two Current FakePromptExecutor Implementations

After the consolidation, two distinct fakes exist, serving different use cases:

<!-- Source: tests/fakes/prompt_executor.py, FakePromptExecutor -->
<!-- Source: packages/erk-shared/src/erk_shared/core/fakes.py, FakePromptExecutor -->

| Aspect               | `tests/fakes/`                                                                                    | `erk_shared/core/fakes`                                                            |
| -------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **Design**           | Scenario-based: `simulated_*` params configure a single predetermined scenario                    | Queue-based: `prompt_results` and `streaming_events` lists consumed in order       |
| **Sequential calls** | Returns same output every time — doesn't support multiple different responses                     | Supports sequential responses via `prompt_results` queue with index tracking       |
| **Call tracking**    | Tracks via internal lists with `.copy()` properties                                               | Tracks via public `NamedTuple` lists (e.g., `PromptCall`, `InteractiveCall`)       |
| **Best for**         | CLI command tests that need rich scenario simulation (PR creation, hook blocking, process errors) | Lower-level tests or erk-shared consumers that need simple prompt result sequences |

See `FakePromptExecutor.__init__()` in each file for the full parameter list. The `tests/fakes/` version uses `simulated_*` prefix naming; the `erk_shared/core/fakes` version uses plain descriptive names (`prompt_results`, `streaming_events`, `passthrough_exit_code`).

## Migration Mapping (Deleted Gateway → Current API)

This table maps the deleted gateway parameters to their current equivalents. The old parameters no longer exist anywhere in the codebase — encountering them means the test needs updating.

| Deleted Gateway Parameter | Current Equivalent (`tests/fakes/`) | Notes                                                                            |
| ------------------------- | ----------------------------------- | -------------------------------------------------------------------------------- |
| `output="text"`           | `simulated_prompt_output="text"`    |                                                                                  |
| `should_fail=True`        | `command_should_fail=True`          | For command execution failures                                                   |
| `error="message"`         | `simulated_prompt_error="message"`  | For prompt execution failures                                                    |
| `transient_failures=2`    | No equivalent                       | Retry logic moved to `RealPromptExecutor` in gateway layer                       |
| `outputs=[...]`           | No equivalent in `tests/fakes/`     | Use `erk_shared/core/fakes` with `prompt_results=[...]` for sequential responses |

Capabilities added in consolidation with no gateway predecessor:

- PR metadata: `simulated_pr_url`, `simulated_pr_number`, `simulated_pr_title`, `simulated_issue_number`
- Hook blocking: `simulated_zero_turns`
- Streaming: `simulated_tool_events`, `simulated_no_output`, `simulated_no_work_events`
- Process errors: `simulated_process_error`

## Which Fake to Choose

| Your test needs...                                                              | Use                                                                      |
| ------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| Simulate a specific execution scenario (PR creation, hook block, process error) | `tests/fakes/prompt_executor.FakePromptExecutor`                         |
| Return different results from sequential `execute_prompt()` calls               | `erk_shared/core/fakes.FakePromptExecutor` with `prompt_results=[...]`   |
| Inject specific `ExecutorEvent` objects into streaming                          | `erk_shared/core/fakes.FakePromptExecutor` with `streaming_events=[...]` |
| Test a CLI command end-to-end with metadata extraction                          | `tests/fakes/prompt_executor.FakePromptExecutor`                         |

## Anti-Pattern: Failure Mode Confusion

The old gateway API had one failure flag (`should_fail`) for everything. The current API distinguishes between failure modes because they have different downstream effects:

- **`command_should_fail`** — the command itself fails (returns `CommandResult` with `success=False` or yields `ErrorEvent`)
- **`simulated_prompt_error`** — the prompt returns a `PromptResult` with `success=False` and an error message
- **`simulated_process_error`** — the subprocess can't start (yields `ProcessErrorEvent`)
- **`simulated_zero_turns`** — Claude completes without doing work, typically from hook blocking (yields `NoTurnsEvent`)
- **`simulated_no_output`** — Claude produces no output at all (yields `NoOutputEvent`)

Using the wrong failure mode produces the wrong event type, which means tests that check for specific error handling paths will pass for the wrong reason.

## Related Documentation

- [PromptExecutor Patterns](../architecture/prompt-executor-patterns.md) — method comparison, when to use each execution mode
