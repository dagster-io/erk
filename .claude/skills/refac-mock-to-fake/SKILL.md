---
name: refac-mock-to-fake
description: >
  Refactor tests that use unittest.mock.patch or MagicMock into erk's gateway-based
  fake pattern. Use when tests import unittest.mock, use @patch decorators, or
  directly call mock.patch() as context managers. Essential when test_*.py files
  patch module-level attributes like subprocess.run, shutil.which, os.environ, or
  other system calls. Covers both making source code injectable AND rewriting tests.
---

# Refactoring Mocks to Fakes

Remove `unittest.mock.patch` from tests by making source code inject gateway
dependencies, then configuring pre-canned fakes in tests.

**Use this skill when**: A test imports `from unittest.mock import patch` or uses
`@patch(...)` decorators.

**Key principle**: Don't stop at the lowest-level matching gateway. Look for a
higher-level abstraction that covers ALL the things being mocked together.

---

## Phase 1: Audit Mock Usage

Read the test file. For each `patch(...)` call, record:

| Mock target (fully qualified)      | What it simulates      | Return value configured                        |
| ---------------------------------- | ---------------------- | ---------------------------------------------- |
| `erk.core.fast_llm.shutil.which`   | CLI availability check | `None` or `"/usr/bin/claude"`                  |
| `erk.core.fast_llm.subprocess.run` | CLI execution result   | `CompletedProcess(returncode=0, stdout="...")` |

**Group mocks by test**: A single test patching 2-3 things together suggests those
things form a unit that should be covered by one injectable gateway.

---

## Phase 2: Gateway Discovery (Critical)

For each mock group, find the right gateway. **Do not stop at the first match.**

### Step 2a: Identify the system boundary being tested

Ask: what is the test _actually_ testing? Not "what function is being patched" but
"what behavior is under test?"

Examples:

- `shutil.which("claude")` -> "is the Claude CLI installed?"
- `subprocess.run(["claude", "--print", ...])` -> "run a prompt via Claude CLI"
- Together -> "execute a prompt when no API key is available"

### Step 2b: Search for existing gateways at the right abstraction level

Search from highest to lowest. A higher-level gateway is preferable because it
covers multiple low-level calls as a unit.

```bash
# 1. Search for existing ABCs that describe the behavior
Grep(pattern="class Fake\w+", path="packages/erk-shared/src/erk_shared/")
Grep(pattern="class Fake\w+", path="tests/fakes/")

# 2. Find gateways that mention the system call you're replacing
Grep(pattern="shutil.which|subprocess.run|is_available", path="packages/erk-shared/")
```

**Priority order when multiple gateways match**:

1. A gateway that covers ALL mocked targets in a test -> inject this one
2. A gateway that covers the highest-level behavior (e.g., `PromptExecutor.execute_prompt`
   rather than `Shell.get_installed_tool_path`)
3. The lowest-level matching gateway as a last resort

**Erk gateway locations**:

- `packages/erk-shared/src/erk_shared/gateway/*/abc.py` -- gateway ABCs
- `packages/erk-shared/src/erk_shared/gateway/*/fake.py` -- matching fakes
- `packages/erk-shared/src/erk_shared/core/fakes.py` -- fakes for service ABCs
  (FakePromptExecutor, FakeLlmCaller, FakeScriptWriter, etc.)
- `tests/fakes/` -- erk-specific fakes

### Step 2c: Verify the fake covers what you need

Read the fake's `__init__` signature. Check:

- Can you configure the pre-canned responses the test needs?
- Does the fake record calls for assertion (`calls`, `prompt_calls`, etc.)?
- Does the fake's `is_available()` return what you need?

If no fake exists at the right level, you'll need to create one (see Phase 4b).

---

## Phase 3: Plan the injection

Identify what source code needs to change.

### Where is the mocked code called from?

Read the source file being patched (e.g., `erk.core.fast_llm` -> `src/erk/core/fast_llm.py`).
Find the class or function that directly calls the mocked thing.

### Is there already a constructor parameter for this gateway?

- **Yes** -> skip Phase 4a, go to Phase 5
- **No** -> plan to add a constructor parameter

### What's the production wiring?

Find where the class is instantiated in production (usually `src/erk/core/context.py`).
Plan what real implementation to wire in:

- `FallbackPromptExecutor` -> `ClaudeCliPromptExecutor(console=None)`
- `Shell` -> `RealShell()`
- etc.

---

## Phase 4a: Make source code injectable

Add the gateway as a constructor parameter. Follow erk's conventions:

- Named parameters only (`def __init__(self, *, gateway: GatewayABC)`)
- No default parameter values -- caller must wire it explicitly
- Store as `self._gateway`

Replace direct system calls with gateway method calls:

```python
# Before:
if shutil.which("claude") is None: ...
result = subprocess.run(["claude", "--print", ...])

# After:
if not self._prompt_executor.is_available(): ...
result = self._prompt_executor.execute_prompt(prompt, model=..., ...)
```

Map gateway return types to the source function's return types. If the gateway
returns `PromptResult(success, output, error)` but the function returns
`LlmResponse | LlmCallFailed`, add the mapping:

```python
if not result.success:
    return LlmCallFailed(message=f"CLI failed: {result.error}")
return LlmResponse(text=result.output)
```

Update production wiring in `context.py`:

```python
from erk.core.prompt_executor import ClaudeCliPromptExecutor
MyClass(prompt_executor=ClaudeCliPromptExecutor(console=None))
```

---

## Phase 4b: Create a new fake (only if needed)

If no suitable fake exists, create one following the 5-place gateway pattern.
See `fake-driven-testing` skill for full guidance.

Short version: the fake should:

- Accept pre-canned responses at construction time
- Record all calls as `NamedTuple` entries in a list (`self.calls: list[MyCall]`)
- Expose calls as a read-only property

---

## Phase 5: Rewrite the tests

For each test that used `patch`:

1. Remove `from unittest.mock import patch` (and any `from subprocess import CompletedProcess`)
2. Construct the fake with pre-canned responses
3. Pass it to the class under test via the new constructor parameter
4. Replace mock assertions (`mock_run.assert_called_once()`) with fake property checks
   (`assert len(executor.prompt_calls) == 1`)

**Pattern**:

```python
# Before:
def test_falls_back_to_cli(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    fake_result = CompletedProcess(args=[], returncode=0, stdout="my-slug\n", stderr="")
    with (
        patch("erk.core.fast_llm.shutil.which", return_value="/usr/bin/claude"),
        patch("erk.core.fast_llm.subprocess.run", return_value=fake_result) as mock_run,
    ):
        result = AnthropicLlmCaller().call("test prompt", system_prompt="sys", max_tokens=50)
    assert isinstance(result, LlmResponse)
    mock_run.assert_called_once()

# After:
def test_falls_back_to_cli(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    executor = FakePromptExecutor(
        prompt_results=[PromptResult(success=True, output="my-slug", error=None)]
    )
    caller = AnthropicLlmCaller(prompt_executor=executor)
    result = caller.call("test prompt", system_prompt="sys", max_tokens=50)
    assert isinstance(result, LlmResponse)
    assert result.text == "my-slug"
    assert len(executor.prompt_calls) == 1
    assert executor.prompt_calls[0].prompt == "test prompt"
```

Note: `monkeypatch.delenv` is a pytest fixture, not `mock.patch` -- it's fine to keep.

---

## Phase 6: Verify

Run the affected test file:

```
uv run pytest <test_file> -v
```

Then lint and type-check the modified source files.

---

## Common pitfalls

**Pitfall 1: Matching the wrong gateway level**
If `shutil.which` is mocked, the obvious match is `Shell.get_installed_tool_path()`.
But if `subprocess.run` is also mocked in the same test, the real abstraction is
something that covers BOTH -- often `PromptExecutor` or a similar higher-level gateway.

**Pitfall 2: `monkeypatch.delenv` vs `mock.patch`**
`monkeypatch.delenv("ANTHROPIC_API_KEY")` is a pytest builtin, not `mock.patch`.
Keep it -- it's acceptable and doesn't need replacement.

**Pitfall 3: Forgetting to update production wiring**
After adding a constructor parameter, always update `context.py` (or wherever the
class is instantiated). The type checker will catch this but only if you run it.

**Pitfall 4: One test, multiple patch contexts**
Multiple `patch()` calls in one test is a red flag that something needs to be at a
higher abstraction level. A single fake should replace all of them.
