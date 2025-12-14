---
title: FakeObjectiveStore Testing Pattern
read_when:
  - "testing objective commands"
  - "writing tests involving objectives"
---

# FakeObjectiveStore Testing Pattern

The `FakeObjectiveStore` enables testing objective commands without filesystem operations.

## Location

- **Interface & Fake**: `packages/erk-shared/src/erk_shared/objectives/storage.py`
- **Example tests**: `tests/commands/objective/test_turn.py`

## Basic Setup

Create `ObjectiveDefinition` and `ObjectiveNotes`, then instantiate `FakeObjectiveStore` with pre-populated state:

```python
from erk_shared.objectives.storage import FakeObjectiveStore
from erk_shared.objectives.types import (
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)


def _create_test_objective() -> ObjectiveDefinition:
    """Create a sample objective for testing."""
    return ObjectiveDefinition(
        name="test-objective",
        objective_type=ObjectiveType.COMPLETABLE,
        desired_state="All tests pass.",
        rationale="Quality assurance.",
        examples=[],
        scope_includes=["src/"],
        scope_excludes=["tests/"],
        evaluation_prompt="Check test coverage.",
        plan_sizing_prompt="Fix 5 tests per plan.",
    )


def test_objective_command() -> None:
    objective = _create_test_objective()
    objectives_store = FakeObjectiveStore(
        objectives={"test-objective": objective},
        notes={"test-objective": ObjectiveNotes(entries=[])},
    )
    # ... use in test
```

## Injecting into Context

Use `build_workspace_test_context()` with the `objectives=` parameter:

```python
from tests.test_utils.context_builders import build_workspace_test_context
from tests.test_utils.env_helpers import erk_isolated_fs_env

def test_turn_command() -> None:
    runner = CliRunner()

    with erk_isolated_fs_env(runner) as env:
        git = FakeGit(
            git_common_dirs={env.cwd: env.git_dir},
            remote_urls={(env.cwd, "origin"): "https://github.com/owner/repo.git"},
        )

        objective = _create_test_objective()
        objectives_store = FakeObjectiveStore(
            objectives={"test-objective": objective},
            notes={"test-objective": ObjectiveNotes(entries=[])},
        )

        ctx = build_workspace_test_context(
            env,
            git=git,
            objectives=objectives_store,  # Inject via keyword argument
        )

        result = runner.invoke(objective_group, ["turn", "test-objective"], obj=ctx)
        assert result.exit_code == 0
```

## Constructor Parameters

| Parameter         | Type                             | Description                       |
| ----------------- | -------------------------------- | --------------------------------- |
| `objectives`      | `dict[str, ObjectiveDefinition]` | Map of name to definition         |
| `notes`           | `dict[str, ObjectiveNotes]`      | Map of name to accumulated notes  |
| `readme_contents` | `dict[str, str]`                 | Map of name to raw README content |
| `notes_contents`  | `dict[str, str]`                 | Map of name to raw notes content  |

## Mutation Tracking

FakeObjectiveStore tracks work log mutations for assertions:

```python
objectives_store = FakeObjectiveStore(
    objectives={"my-objective": objective},
    notes={},
)

# Run command that appends to work log...

# Assert work log entries were created
assert len(objectives_store.work_log_entries) == 1
name, entry = objectives_store.work_log_entries[0]
assert name == "my-objective"
assert entry.event_type == "turn_completed"
```

## Testing Nonexistent Objectives

To test error handling for missing objectives:

```python
def test_fails_for_nonexistent_objective() -> None:
    objectives_store = FakeObjectiveStore(objectives={}, notes={})

    ctx = build_workspace_test_context(
        env,
        git=git,
        objectives=objectives_store,
    )

    result = runner.invoke(objective_group, ["turn", "nonexistent"], obj=ctx)

    assert result.exit_code == 1
    assert "Objective not found" in result.output
```

## Combined with FakeClaudeExecutor

Objective commands often launch Claude. Combine both fakes:

```python
from tests.fakes.claude_executor import FakeClaudeExecutor

objectives_store = FakeObjectiveStore(
    objectives={"test-objective": objective},
    notes={"test-objective": ObjectiveNotes(entries=[])},
)

claude_executor = FakeClaudeExecutor(claude_available=True)

ctx = build_workspace_test_context(
    env,
    git=git,
    objectives=objectives_store,
    claude_executor=claude_executor,
)

# After test - check execute_interactive was called
assert len(claude_executor.interactive_calls) == 1
worktree_path, dangerous, command, target_subpath = claude_executor.interactive_calls[0]
```

## Related Documentation

- [ClaudeExecutor Pattern Documentation](../architecture/claude-executor-patterns.md) - Testing Claude execution
- [Testing Overview](testing.md) - General testing patterns
