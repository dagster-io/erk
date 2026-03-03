# E2E Integration Tests Using Claude Agent SDK

## Context

Erk currently has no end-to-end tests that exercise the full Claude Code planning workflow. All tests use `FakePromptExecutor` to simulate Claude behavior, which means the actual LLM-driven planning/implementation cycle is untested. We need integration tests that run Claude Code against real code, driven by an LLM (Claude itself), testing the full interactive planning workflow.

The key insight: Claude Code's terminal is dynamic and unpredictable, so static pattern matching (tmux/pexpect) won't work. Instead, we use the **Python Claude Agent SDK** (`claude-agent-sdk`) which runs the same Claude Code agent loop (same tools, same model, same file editing) but with programmatic multi-turn conversation control. The LLM drives the interaction - we just provide the prompts and assert on outcomes.

## Approach: Python Claude Agent SDK with `ClaudeSDKClient`

The SDK provides `ClaudeSDKClient` for multi-turn conversations:
- Maintains session context across multiple exchanges
- Full access to all Claude Code tools (Read, Write, Edit, Bash, etc.)
- Permission control (`permission_mode`, `can_use_tool`)
- Same agent loop as interactive Claude Code
- Python-native (fits erk's stack)

## Implementation

### 1. Add `claude-agent-sdk` dev dependency

Add to `pyproject.toml` under dev dependencies:
```
claude-agent-sdk
```

Install via `uv add --dev claude-agent-sdk`.

### 2. Create test directory structure

```
tests/
  e2e/
    __init__.py
    conftest.py          # Fixtures: temp repo, SDK client, cleanup
    helpers.py           # Shared utilities
    test_hello_world.py  # First test: plan + implement hello world
```

### 3. Core fixtures (`tests/e2e/conftest.py`)

**`temp_python_repo` fixture:**
- Creates a tmp_path git repo with `main.py` containing a simple function
- Initializes git with an initial commit
- Returns the repo Path

**`claude_client` fixture:**
- Creates a `ClaudeSDKClient` with options:
  - `cwd` = temp repo path
  - `permission_mode` = `"bypassPermissions"` (no approval prompts in tests)
  - `allow_dangerously_skip_permissions` = `True`
  - `max_turns` = 30 (enough for plan + implement)
  - `system_prompt` = preset `claude_code` (loads full Claude Code behavior)
  - `setting_sources` = `[]` (isolated from user settings)
  - `persist_session` = `False` (no session files left behind)
- Uses async context manager for cleanup
- Returns the connected client

### 4. Helper utilities (`tests/e2e/helpers.py`)

```python
async def collect_response(client: ClaudeSDKClient) -> tuple[str, list[Message]]:
    """Collect all messages from a response, return (text, all_messages)."""
    text_parts = []
    messages = []
    async for message in client.receive_response():
        messages.append(message)
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
    return "\n".join(text_parts), messages

def assert_file_contains(path: Path, substring: str) -> None:
    """Assert a file exists and contains the given substring."""
    assert path.exists(), f"File {path} does not exist"
    content = path.read_text()
    assert substring in content, f"'{substring}' not found in {path}"
```

### 5. First test: Hello World Plan (`tests/e2e/test_hello_world.py`)

```python
import asyncio
import subprocess
from pathlib import Path

import pytest
from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
)

from tests.e2e.helpers import assert_file_contains, collect_response


@pytest.fixture
def temp_python_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "test-repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test.com"], cwd=repo, check=True
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"], cwd=repo, check=True
    )
    (repo / "main.py").write_text(
        "# Main module\n\ndef greet(name: str) -> str:\n    return f'Hi {name}'\n"
    )
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=repo, check=True
    )
    return repo


@pytest.mark.asyncio
async def test_hello_world_plan_and_implement(temp_python_repo: Path) -> None:
    """Test the full planning workflow: plan, approve, implement, verify."""
    options = ClaudeAgentOptions(
        cwd=str(temp_python_repo),
        permission_mode="bypassPermissions",
        allow_dangerously_skip_permissions=True,
        max_turns=30,
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=[],
        persist_session=False,
    )

    async with ClaudeSDKClient(options) as client:
        # Turn 1: Ask Claude to create a plan
        await client.query(
            "I want to add a print('Hello, world!') statement to main.py. "
            "First, read the file and tell me your plan for where to add it. "
            "Do NOT make any changes yet - just describe your plan."
        )
        plan_text, _ = await collect_response(client)

        # Verify Claude produced a plan mentioning the file
        assert "main.py" in plan_text.lower() or "hello" in plan_text.lower()

        # Turn 2: Approve and implement
        await client.query(
            "That plan looks good. Go ahead and implement it now - "
            "add print('Hello, world!') to main.py."
        )
        impl_text, _ = await collect_response(client)

        # Verify the file was modified
        assert_file_contains(temp_python_repo / "main.py", "Hello, world!")
```

### 6. Extended test: Plan-Save and Plan-Implement (future)

Once the basic test works, extend to test the full erk workflow:

```python
@pytest.mark.asyncio
async def test_plan_save_and_implement(temp_python_repo: Path) -> None:
    """Test plan-save followed by plan-implement in a new session."""
    # Session 1: Create and save plan
    # Session 2: Implement from saved plan in a worktree
    # Verify file changes
    # Cleanup GitHub artifacts
    ...
```

This requires a GitHub-connected repo and would create real draft PRs. Defer until the basic test is working.

### 7. pytest configuration

Add to `pyproject.toml`:
```toml
[tool.pytest.ini_options]
markers = ["e2e: end-to-end tests requiring Claude API access"]
asyncio_mode = "auto"
```

Add `pytest-asyncio` dev dependency if not already present.

E2E tests should be excluded from `make test` (unit tests only) and run separately:
```bash
uv run pytest tests/e2e/ -m e2e -v
```

### 8. Makefile target

Add a `test-e2e` target:
```makefile
test-e2e:
    uv run pytest tests/e2e/ -v --timeout=300
```

## Key Files to Modify

- `pyproject.toml` — add `claude-agent-sdk`, `pytest-asyncio` dev deps, e2e marker
- `Makefile` — add `test-e2e` target
- `tests/e2e/__init__.py` — new (empty)
- `tests/e2e/conftest.py` — new (fixtures)
- `tests/e2e/helpers.py` — new (utilities)
- `tests/e2e/test_hello_world.py` — new (first test)

## Verification

1. Install deps: `uv sync`
2. Run the test: `uv run pytest tests/e2e/test_hello_world.py -v --timeout=300`
3. Confirm:
   - Claude reads `main.py` in turn 1 and describes a plan
   - Claude modifies `main.py` in turn 2 to add `print('Hello, world!')`
   - Test passes with assertions on file content
4. Check no session artifacts left behind (persist_session=False)

## Notes

- Tests require a valid Anthropic API key (from environment or Claude Code auth)
- Tests cost real API tokens (~$0.05-0.10 per run)
- Tests are non-deterministic (LLM output varies) — assertions should be loose
- Timeout of 300s accounts for API latency
- `setting_sources=[]` ensures tests don't pick up user/project settings
