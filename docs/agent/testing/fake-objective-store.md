---
title: FakeObjectiveStore Testing Pattern
read_when:
  - "testing objective commands"
  - "writing tests with FakeObjectiveStore"
  - "setting up objective test fixtures"
---

# FakeObjectiveStore Testing Pattern

The `FakeObjectiveStore` enables testing objective commands without filesystem operations.

## Overview

`FakeObjectiveStore` is an in-memory implementation of the `ObjectiveStore` ABC that operates purely on data structures passed at construction time.

**Location**: `packages/erk-shared/src/erk_shared/objectives/storage.py`

**Purpose**: Test objective-related commands and logic without touching the filesystem.

## Basic Setup

### 1. Create Test Data

First, construct the objective definition and notes:

```python
from erk_shared.objectives.types import (
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)

definition = ObjectiveDefinition(
    name="test-objective",
    objective_type=ObjectiveType.COMPLETABLE,
    desired_state="All Python files use modern type syntax",
    rationale="Improve type safety and code clarity",
    examples="str | None instead of Optional[str]",
    scope_includes=["src/**/*.py"],
    scope_excludes=["tests/"],
    evaluation_prompt="Check for old-style type hints",
    plan_sizing_prompt="Keep changes under 5 files per plan",
)

notes = ObjectiveNotes(
    notes=["Turn 1: Found 10 files needing updates"]
)
```

### 2. Create FakeObjectiveStore

Instantiate with pre-populated data:

```python
from erk_shared.objectives.storage import FakeObjectiveStore

store = FakeObjectiveStore(
    objectives={"test-objective": definition},
    notes={"test-objective": notes},
)
```

### 3. Inject into Context

Use the test context builder with the `objectives` parameter:

```python
from tests.test_utils.context_builders import build_workspace_test_context

ctx = build_workspace_test_context(
    cwd=repo_root,
    objectives=store,
)
```

## Complete Test Example

```python
from pathlib import Path
from erk_shared.objectives.types import (
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)
from erk_shared.objectives.storage import FakeObjectiveStore
from tests.test_utils.context_builders import build_workspace_test_context

def test_list_objectives():
    """Test listing objectives."""
    repo_root = Path("/fake/repo")

    # Setup
    definition = ObjectiveDefinition(
        name="test-objective",
        objective_type=ObjectiveType.COMPLETABLE,
        desired_state="Test state",
        rationale="Test rationale",
        examples="Test examples",
        scope_includes=["src/"],
        scope_excludes=[],
        evaluation_prompt="Test evaluation",
        plan_sizing_prompt="Test sizing",
    )

    store = FakeObjectiveStore(
        objectives={"test-objective": definition},
        notes={"test-objective": ObjectiveNotes(notes=[])},
    )

    ctx = build_workspace_test_context(
        cwd=repo_root,
        objectives=store,
    )

    # Execute
    objectives = ctx.objectives.list_objectives()

    # Assert
    assert len(objectives) == 1
    assert objectives[0].name == "test-objective"
```

## Testing Objective Commands

When testing Click commands that use objectives:

```python
from click.testing import CliRunner
from erk.cli.commands.objective.list_cmd import list_objectives

def test_list_command():
    """Test 'erk objective list' command."""
    runner = CliRunner()

    # Setup fake store
    store = FakeObjectiveStore(
        objectives={"test-obj": definition},
        notes={"test-obj": ObjectiveNotes(notes=[])},
    )

    ctx = build_workspace_test_context(objectives=store)

    # Execute
    result = runner.invoke(list_objectives, obj=ctx)

    # Assert
    assert result.exit_code == 0
    assert "test-obj" in result.output
```

## Key Principles

### 1. All State via Constructor

The fake accepts all state at construction - no public setup methods:

```python
# ✅ CORRECT
store = FakeObjectiveStore(
    objectives={"name": definition},
    notes={"name": notes},
)

# ❌ WRONG - no setup methods exist
store = FakeObjectiveStore()
store.add_objective(definition)  # This method doesn't exist
```

### 2. No Filesystem Operations

The fake operates entirely in-memory:

```python
# Store operates on in-memory dictionaries
store.get_objective("test-obj")  # Returns from dict, no disk I/O
```

### 3. Consistent with Real Implementation

The fake implements the same `ObjectiveStore` ABC as `RealObjectiveStore`, ensuring tests accurately reflect production behavior.

## Common Patterns

### Empty Store

```python
store = FakeObjectiveStore()  # No objectives
```

### Multiple Objectives

```python
store = FakeObjectiveStore(
    objectives={
        "obj-1": definition_1,
        "obj-2": definition_2,
    },
    notes={
        "obj-1": ObjectiveNotes(notes=["Note 1"]),
        "obj-2": ObjectiveNotes(notes=[]),
    },
)
```

### Testing Not Found Scenarios

```python
store = FakeObjectiveStore()  # Empty
result = store.get_objective("nonexistent")
assert result is None  # Or check for appropriate sentinel
```

## Related Documentation

- [Erk Test Reference](testing.md) — test structure and fake patterns
- Load `fake-driven-testing` skill — testing philosophy
- [Objectives System](../glossary.md#objectives-system) — objective concepts
