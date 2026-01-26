---
title: Prompt Executor Gateway
read_when:
  - "executing LLM prompts from Python code"
  - "testing code that uses Claude CLI"
  - "implementing single-shot prompt execution"
  - "working with PromptExecutor or FakePromptExecutor"
---

# Prompt Executor Gateway

A minimal 3-file gateway abstraction for executing single-shot prompts via Claude CLI. Designed for kit CLI commands that need to generate content via AI.

## Package Location

```
packages/erk-shared/src/erk_shared/prompt_executor/
├── __init__.py
├── abc.py      # Abstract interface + PromptResult type
├── real.py     # Production implementation with retry logic
└── fake.py     # Test implementation with configurable behavior
```

## Why a Simplified Gateway?

Unlike the full `ClaudeExecutor` in erk core (which supports streaming and interactive commands), `PromptExecutor` is deliberately minimal:

- **Single-shot only**: No streaming, no interactive commands
- **3-file structure**: ABC, real, fake (no dry-run wrapper needed)
- **Fast to understand**: Entire interface fits in ~50 lines

This simplicity makes it ideal for objective workflows that just need to send a prompt and get a response.

## Interface

### PromptResult

Result of executing a single prompt:

| Field     | Type          | Description                              |
| --------- | ------------- | ---------------------------------------- |
| `success` | `bool`        | Whether the prompt completed             |
| `output`  | `str`         | Output text (empty string on failure)    |
| `error`   | `str \| None` | Error message if failed, None on success |

### PromptExecutor ABC

```python
class PromptExecutor(ABC):
    @abstractmethod
    def execute_prompt(
        self,
        prompt: str,
        *,
        model: str,
        cwd: Path | None = None,
    ) -> PromptResult:
        """Execute a single prompt and return the result.

        Model selection varies by subsystem and use case. Callers should
        explicitly specify the model based on task complexity and latency needs.
        """
        ...
```

## Production Implementation

`RealPromptExecutor` uses subprocess to call Claude CLI:

```python
executor = RealPromptExecutor(time=RealTime())
result = executor.execute_prompt(
    "Generate a commit message for this diff",
    model="sonnet",  # Model selection based on task complexity
    cwd=repo_root,
)
if result.success:
    print(result.output)
```

### Retry Logic

`RealPromptExecutor` retries on transient empty-output failures:

- Success with non-empty output → return immediately
- Success with empty output → retry with exponential backoff
- Actual failure → return failure

Retry delays: `[0.5, 1.0]` seconds (~1.5s max, 2 retries)

### CLI Flags Used

```bash
claude --print --no-session-persistence --model <model> --dangerously-skip-permissions
```

- `--print`: Single-shot mode (no conversation)
- `--no-session-persistence`: Don't save session
- `--dangerously-skip-permissions`: Skip permission prompts (agent context)

## Test Implementation

`FakePromptExecutor` supports multiple test scenarios via constructor injection:

### Basic Usage

```python
executor = FakePromptExecutor(output='["1. First step", "2. Second step"]')
result = executor.execute_prompt("Extract steps", model="haiku")
assert result.success
assert result.output == '["1. First step", "2. Second step"]'
```

### Simulating Failures

```python
executor = FakePromptExecutor(should_fail=True, error="API rate limit exceeded")
result = executor.execute_prompt("test")
assert not result.success
assert result.error == "API rate limit exceeded"
```

### Sequential Responses

For workflows making multiple LLM calls:

```python
executor = FakePromptExecutor(outputs=["First response", "Second response"])
result1 = executor.execute_prompt("first call")
assert result1.output == "First response"
result2 = executor.execute_prompt("second call")
assert result2.output == "Second response"
# Additional calls return the last output
result3 = executor.execute_prompt("third call")
assert result3.output == "Second response"
```

### Transient Failures (Retry Testing)

Simulates empty-output responses that trigger retry logic:

```python
executor = FakePromptExecutor(output="Success!", transient_failures=2)
# First two calls return success with empty output
result1 = executor.execute_prompt("test")
assert result1.success and result1.output == ""
result2 = executor.execute_prompt("test")
assert result2.success and result2.output == ""
# Third call returns actual output
result3 = executor.execute_prompt("test")
assert result3.success and result3.output == "Success!"
```

### Inspecting Calls

```python
executor = FakePromptExecutor(output="test")
executor.execute_prompt("my prompt", model="sonnet")

assert len(executor.prompt_calls) == 1
assert executor.prompt_calls[0].prompt == "my prompt"
assert executor.prompt_calls[0].model == "sonnet"
```

## Constructor Parameters

| Parameter            | Type          | Default | Description                              |
| -------------------- | ------------- | ------- | ---------------------------------------- |
| `output`             | `str`         | `"[]"`  | Output for successful calls              |
| `outputs`            | `list[str]`   | `None`  | Sequence of outputs for successive calls |
| `error`              | `str \| None` | `None`  | Error message for failures               |
| `should_fail`        | `bool`        | `False` | Whether to return failure                |
| `transient_failures` | `int`         | `0`     | Empty responses before success           |

## Time Dependency

`RealPromptExecutor` requires a `Time` dependency for testable sleep operations:

```python
from erk_shared.gateway.time.real import RealTime
from erk_shared.gateway.time.fake import FakeTime

# Production
executor = RealPromptExecutor(time=RealTime())

# Testing (instant "sleep")
executor = RealPromptExecutor(time=FakeTime())
```

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) - Full 5-file gateway pattern
