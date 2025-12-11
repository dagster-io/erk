# Plan: Add Pure Logic Extraction Pattern to fake-driven-testing Skill

## Summary

Add documentation for the "Pure Logic Extraction" pattern to the fake-driven-testing skill's `patterns.md` reference file.

## File to Modify

`packages/dot-agent-kit/src/dot_agent_kit/data/kits/fake-driven-testing/skills/fake-driven-testing/references/patterns.md`

## Content to Add

New section after existing patterns (Constructor Injection, Mutation Tracking, etc.):

```markdown
## Pure Logic Extraction Pattern

**Pattern**: Separate decision logic from I/O by extracting pure functions that take input dataclasses and return output dataclasses.

**Use when**: Testing hooks, CLI commands, or any code with many external dependencies that would require heavy mocking.

### The Problem

Hooks and CLI commands often have many I/O dependencies:
- Reading stdin/environment
- Calling subprocess (git, etc.)
- Reading/writing files
- Checking file existence

Testing these requires mocking every dependency, leading to brittle tests with 3-5+ patches per test.

### The Solution

1. **Input Dataclass**: Capture all inputs needed for decision logic
2. **Pure Function**: All decision logic, no I/O
3. **Output Dataclass**: Decision result including what actions to take
4. **I/O Wrappers**: Thin functions that gather inputs and execute outputs

### Implementation

```python
from dataclasses import dataclass
from enum import Enum

class Action(Enum):
    ALLOW = 0
    BLOCK = 2

@dataclass(frozen=True)
class HookInput:
    """All inputs needed for decision logic."""
    session_id: str | None
    feature_enabled: bool
    marker_exists: bool
    plan_exists: bool

@dataclass(frozen=True)
class HookOutput:
    """Decision result from pure logic."""
    action: Action
    message: str
    delete_marker: bool = False

def determine_action(hook_input: HookInput) -> HookOutput:
    """Pure function - all decision logic, no I/O."""
    if not hook_input.feature_enabled:
        return HookOutput(Action.ALLOW, "")

    if hook_input.session_id is None:
        return HookOutput(Action.ALLOW, "No session")

    if hook_input.marker_exists:
        return HookOutput(Action.ALLOW, "Marker found", delete_marker=True)

    if hook_input.plan_exists:
        return HookOutput(Action.BLOCK, "Plan exists - prompting user")

    return HookOutput(Action.ALLOW, "No plan found")

# I/O layer
def _gather_inputs() -> HookInput:
    """All I/O happens here."""
    return HookInput(
        session_id=_get_session_from_stdin(),
        feature_enabled=_is_feature_enabled(),
        marker_exists=_marker_path().exists() if _marker_path() else False,
        plan_exists=_find_plan() is not None,
    )

def _execute_result(result: HookOutput) -> None:
    """All I/O happens here."""
    if result.delete_marker:
        _marker_path().unlink()
    click.echo(result.message, err=True)
    sys.exit(result.action.value)

# Main entry point
def hook_command() -> None:
    hook_input = _gather_inputs()
    result = determine_action(hook_input)
    _execute_result(result)
```

### Testing Benefits

**Before (mocking):**
```python
def test_marker_allows_exit(tmp_path):
    with (
        patch("module.is_in_project", return_value=True),
        patch("subprocess.run", return_value=mock_result),
        patch("module.extract_slugs", return_value=["slug"]),
        patch("module._get_branch", return_value="main"),
        patch("pathlib.Path.home", return_value=tmp_path),
    ):
        result = runner.invoke(hook_command, input=stdin_data)
    assert result.exit_code == 0
```

**After (pure logic):**
```python
def test_marker_allows_exit():
    result = determine_action(HookInput(
        session_id="abc123",
        feature_enabled=True,
        marker_exists=True,
        plan_exists=True,
    ))
    assert result.action == Action.ALLOW
    assert result.delete_marker is True
```

### When to Use

- Hooks with 3+ external dependencies
- CLI commands with complex conditional logic
- Any code where test setup dominates test assertions

### Results

| Metric | Before | After |
|--------|--------|-------|
| Pure logic tests (no mocking) | 0 | 12 |
| Integration tests (mocking) | 13 | 3 |
| Patches per integration test | 3-5 | 2 |
```

## Implementation Notes

- Add as new section in patterns.md
- Position after existing patterns (Constructor Injection, Mutation Tracking, CliRunner, etc.)
- Example is based on the actual `exit_plan_mode_hook.py` refactoring from this session