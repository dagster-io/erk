---
title: Prompt Executor Gateway
read_when:
  - "executing LLM prompts from Python code"
  - "testing code that uses Claude CLI"
  - "implementing single-shot prompt execution"
  - "working with PromptExecutor or FakePromptExecutor"
tripwires:
  - "execute_prompt() supports both single-shot and streaming modes - choose based on whether you need real-time updates"
  - "FakePromptExecutor tracks all calls via properties - use .prompt_calls, .interactive_calls, .passthrough_calls for assertions"
  - "execute_interactive() never returns in production - it replaces the process via os.execvp"
---

# Prompt Executor Gateway

The `PromptExecutor` abstraction enables executing Claude CLI commands from Python without subprocess mocking. It provides three execution modes (streaming, single-shot, passthrough) and comprehensive fake support for testing.

## Why Three Execution Modes?

The abstraction supports fundamentally different integration patterns:

| Mode                           | Returns                   | Output                           | Use Case                                                                |
| ------------------------------ | ------------------------- | -------------------------------- | ----------------------------------------------------------------------- |
| `execute_command_streaming()`  | `Iterator[ExecutorEvent]` | Yields typed events in real-time | Real-time progress displays, extracting PR metadata during execution    |
| `execute_prompt()`             | `PromptResult`            | Captures output string           | Simple prompt-and-response, commit message generation, title extraction |
| `execute_prompt_passthrough()` | `int` (exit code)         | Streams to terminal              | Code review, user-facing output where Claude's formatting matters       |
| `execute_interactive()`        | Never returns             | Replaces process                 | Launching Claude for interactive sessions (erk prepare, erk edit)       |

**Design rationale**: Single abstraction with mode selection beats four separate abstractions. Callers choose the mode that matches their integration needs. The fake implements all modes, so tests can verify mode selection without subprocess overhead.

## Streaming vs Single-Shot Trade-offs

**Streaming** (`execute_command_streaming`):

- Yields `ExecutorEvent` objects as they occur
- Enables real-time UI updates (spinners, progress bars)
- Can extract PR metadata mid-execution
- Must handle event stream complexity

**Single-shot** (`execute_prompt`):

- Returns final output as string
- Simpler API for fire-and-forget prompts
- Cannot show progress during execution
- Best for batch operations, background tasks

Choose streaming when the user is waiting and needs feedback. Choose single-shot when the result matters more than the process.

## Model Selection Philosophy

**The caller specifies the model**. PromptExecutor does not pick models because different use cases prioritize different trade-offs:

- Commit message generation: `model="haiku"` (fast, cheap, good enough)
- Code review synthesis: `model="sonnet"` (accuracy matters)
- Interactive planning: `model="opus"` (complex reasoning needed)

This forces explicit decisions at call sites instead of hiding them in the abstraction.

## Fake Implementation Patterns

<!-- Source: tests/fakes/prompt_executor.py, FakePromptExecutor -->

The fake uses **constructor injection** to configure all behaviors. No setters, no mutation after construction. See `FakePromptExecutor.__init__()` in `tests/fakes/prompt_executor.py`.

### Simulating Failures

The fake distinguishes between failure types because callers handle them differently:

**Process errors** (Claude CLI not found, permission denied):

```python
FakePromptExecutor(simulated_process_error="Permission denied")
# Yields ProcessErrorEvent - simulates Popen failure
```

**No output** (Claude ran but produced nothing):

```python
FakePromptExecutor(simulated_no_output=True)
# Yields NoOutputEvent - simulates empty stdout
```

**Hook blocking** (command completed without turns):

```python
FakePromptExecutor(simulated_zero_turns=True)
# Yields NoTurnsEvent - simulates hook rejection
```

**Command failure** (non-zero exit code):

```python
FakePromptExecutor(command_should_fail=True)
# Yields ErrorEvent - simulates Claude execution failure
```

**Why distinguish?** Each failure mode triggers different error messages and recovery logic. The fake enables testing all branches without subprocess manipulation.

### Precedence Rules

When multiple failure modes are configured, the fake applies precedence:

1. `simulated_process_error` (Popen never succeeds)
2. `simulated_no_output` (process ran, no stdout)
3. `simulated_zero_turns` (process ran, hook blocked)
4. `command_should_fail` (process ran, exited non-zero)

<!-- Source: tests/unit/fakes/test_fake_prompt_executor.py -->

See `test_fake_prompt_executor_process_error_takes_precedence()` in `tests/unit/fakes/test_fake_prompt_executor.py` for precedence verification.

### Call Tracking

The fake records all calls for assertion:

```python
executor = FakePromptExecutor()
executor.execute_prompt("Generate title", model="haiku", dangerous=True)

assert len(executor.prompt_calls) == 1
assert executor.prompt_calls[0] == ("Generate title", None, True)
#                                    prompt           system_prompt  dangerous
```

**All tracking properties return copies** to prevent test pollution. Modifying `executor.prompt_calls` does not affect the fake's internal state.

## Interactive Execution Asymmetry

`execute_interactive()` has fundamentally different behavior in real vs fake:

**Production** (`ClaudePromptExecutor`):

- Calls `os.execvp()` to replace current process
- Never returns
- Terminates the Python interpreter

**Fake** (`FakePromptExecutor`):

- Records the call
- Returns normally
- Allows tests to continue and make assertions

This asymmetry is intentional. Tests verify that interactive execution was _requested_ with correct parameters, not that the process was actually replaced.

## TTY Redirection Logic

<!-- Source: src/erk/core/prompt_executor.py, ClaudePromptExecutor.execute_interactive -->

`execute_interactive()` conditionally redirects stdin/stdout/stderr to `/dev/tty` only when they are not already TTYs. See `ClaudePromptExecutor.execute_interactive()` in `src/erk/core/prompt_executor.py`.

**Why conditional?** When erk runs as a subprocess with captured stdout (shell integration), Claude needs terminal access. But when stdout is already a TTY (normal terminal), redirection breaks tools like Bun that expect specific TTY capabilities.

**The Console dependency** (`self._console.is_stdout_tty()`) enables testing this logic without actual file descriptors.

## PromptResult vs CommandResult

Two result types because two integration patterns:

**PromptResult** (from `execute_prompt()`):

- Success/failure boolean
- Output string
- Error message on failure
- Minimal - just the essentials for single-shot prompts

**CommandResult** (from `execute_command()`):

- Everything from PromptResult
- Plus PR metadata (URL, number, title)
- Plus issue linkage
- Plus execution duration
- Plus filtered messages list

`execute_command()` is implemented as a wrapper around `execute_command_streaming()` that collects events and builds `CommandResult`. This avoids duplicating the streaming logic.

## Type Discrimination in Events

<!-- Source: packages/erk-shared/src/erk_shared/core/prompt_executor.py, ExecutorEvent -->

`ExecutorEvent` is a discriminated union of event types. See the event type definitions in `packages/erk-shared/src/erk_shared/core/prompt_executor.py`.

Consumers use pattern matching to dispatch:

```python
for event in executor.execute_command_streaming(...):
    match event:
        case TextEvent(content=text):
            print(text)
        case PrUrlEvent(url=url):
            save_pr_url(url)
        case ErrorEvent(message=msg):
            log_error(msg)
```

**Why not inheritance with polymorphic dispatch?** Pattern matching makes the event types explicit at call sites. Readers see all handled cases. Frozen dataclasses prevent mutation bugs.

## Shared ABC, Divergent Implementations

<!-- Source: packages/erk-shared/src/erk_shared/core/prompt_executor.py, PromptExecutor -->
<!-- Source: src/erk/core/prompt_executor.py, ClaudePromptExecutor -->
<!-- Source: packages/erk-shared/src/erk_shared/core/fakes.py, FakePromptExecutor (erk-shared) -->
<!-- Source: tests/fakes/prompt_executor.py, FakePromptExecutor (erk) -->

The ABC lives in `erk-shared` (packages/erk-shared/src/erk_shared/core/prompt_executor.py). The real implementation lives in `erk` core (src/erk/core/prompt_executor.py). There are **two** fake implementations:

1. **erk-shared fake** (`packages/erk-shared/src/erk_shared/core/fakes.py`): Minimal fake for erk-kits and external consumers
2. **erk fake** (`tests/fakes/prompt_executor.py`): Full-featured fake with comprehensive error simulation

**Why two fakes?** The erk-shared fake has no erk dependencies and can be used by packages that import the ABC but not the real implementation. The erk fake includes erk-specific testing features like hook blocking simulation.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full 5-file gateway pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) - Event type design rationale
