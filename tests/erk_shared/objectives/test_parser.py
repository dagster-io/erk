"""Tests for objective definition and notes parsers."""

import pytest

from erk_shared.objectives.parser import (
    parse_objective_definition,
    parse_objective_notes,
)
from erk_shared.objectives.types import ObjectiveType


class TestParseObjectiveDefinition:
    """Tests for parse_objective_definition."""

    def test_parses_completable_objective(self) -> None:
        """Should parse a complete objective definition with completable type."""
        content = """# Objective: cli-ensure-error-handling

## Type
completable

## Desired State
All error handling in CLI commands should use the Ensure class pattern instead
of raw exception handling.

## Rationale
Consistent error handling improves maintainability and provides better error
messages to users.

## Examples
Before:
```python
if not path.exists():
    raise ValueError(f"Path not found: {path}")
```

After:
```python
Ensure.invariant(path.exists(), f"Path not found: {path}")
```

## Scope
### In Scope
- src/erk/cli/commands/
- src/erk/core/

### Out of Scope
- tests/
- third-party integrations

## Turn Configuration
### Evaluation Prompt
Search for direct exception raising patterns in CLI code and identify
opportunities to use Ensure class methods.

### Plan Sizing
Limit each plan to 5-10 files maximum to keep changes reviewable.
"""

        result = parse_objective_definition("cli-ensure-error-handling", content)

        assert result.name == "cli-ensure-error-handling"
        assert result.objective_type == ObjectiveType.COMPLETABLE
        assert "Ensure class pattern" in result.desired_state
        assert "maintainability" in result.rationale
        assert len(result.examples) == 1
        assert "Before:" in result.examples[0]
        assert result.scope_includes == ["src/erk/cli/commands/", "src/erk/core/"]
        assert result.scope_excludes == ["tests/", "third-party integrations"]
        assert "exception raising patterns" in result.evaluation_prompt
        assert "5-10 files" in result.plan_sizing_prompt

    def test_parses_perpetual_objective(self) -> None:
        """Should parse a perpetual type objective."""
        content = """# Objective: no-direct-sleep

## Type
perpetual

## Desired State
No direct calls to time.sleep() in the codebase.

## Rationale
Direct sleep calls make tests slow and non-deterministic.

## Turn Configuration
### Evaluation Prompt
Search for time.sleep() calls.

### Plan Sizing
Fix all violations in one plan.
"""

        result = parse_objective_definition("no-direct-sleep", content)

        assert result.objective_type == ObjectiveType.PERPETUAL

    def test_raises_on_missing_type(self) -> None:
        """Should raise ValueError if Type section is missing."""
        content = """# Objective: test

## Desired State
Some state.

## Rationale
Some reason.

## Turn Configuration
### Evaluation Prompt
prompt

### Plan Sizing
sizing
"""

        with pytest.raises(ValueError, match="Missing required section: Type"):
            parse_objective_definition("test", content)

    def test_raises_on_invalid_type(self) -> None:
        """Should raise ValueError for invalid type value."""
        content = """# Objective: test

## Type
invalid_type

## Desired State
Some state.

## Rationale
Some reason.

## Turn Configuration
### Evaluation Prompt
prompt

### Plan Sizing
sizing
"""

        with pytest.raises(ValueError, match="Invalid objective type"):
            parse_objective_definition("test", content)

    def test_raises_on_missing_desired_state(self) -> None:
        """Should raise ValueError if Desired State section is missing."""
        content = """# Objective: test

## Type
completable

## Rationale
Some reason.

## Turn Configuration
### Evaluation Prompt
prompt

### Plan Sizing
sizing
"""

        with pytest.raises(ValueError, match="Missing required section: Desired State"):
            parse_objective_definition("test", content)

    def test_raises_on_missing_rationale(self) -> None:
        """Should raise ValueError if Rationale section is missing."""
        content = """# Objective: test

## Type
completable

## Desired State
Some state.

## Turn Configuration
### Evaluation Prompt
prompt

### Plan Sizing
sizing
"""

        with pytest.raises(ValueError, match="Missing required section: Rationale"):
            parse_objective_definition("test", content)

    def test_raises_on_missing_turn_configuration(self) -> None:
        """Should raise ValueError if Turn Configuration section is missing."""
        content = """# Objective: test

## Type
completable

## Desired State
Some state.

## Rationale
Some reason.
"""

        with pytest.raises(ValueError, match="Missing required section: Turn Configuration"):
            parse_objective_definition("test", content)

    def test_raises_on_missing_evaluation_prompt(self) -> None:
        """Should raise ValueError if Evaluation Prompt subsection is missing."""
        content = """# Objective: test

## Type
completable

## Desired State
Some state.

## Rationale
Some reason.

## Turn Configuration
### Plan Sizing
sizing
"""

        with pytest.raises(
            ValueError, match="Missing required subsection: Turn Configuration > Evaluation Prompt"
        ):
            parse_objective_definition("test", content)

    def test_raises_on_missing_plan_sizing(self) -> None:
        """Should raise ValueError if Plan Sizing subsection is missing."""
        content = """# Objective: test

## Type
completable

## Desired State
Some state.

## Rationale
Some reason.

## Turn Configuration
### Evaluation Prompt
prompt
"""

        with pytest.raises(
            ValueError, match="Missing required subsection: Turn Configuration > Plan Sizing"
        ):
            parse_objective_definition("test", content)

    def test_handles_empty_scope(self) -> None:
        """Should handle objective with no scope section."""
        content = """# Objective: test

## Type
completable

## Desired State
Some state.

## Rationale
Some reason.

## Turn Configuration
### Evaluation Prompt
prompt

### Plan Sizing
sizing
"""

        result = parse_objective_definition("test", content)

        assert result.scope_includes == []
        assert result.scope_excludes == []

    def test_handles_empty_examples(self) -> None:
        """Should handle objective with no examples section."""
        content = """# Objective: test

## Type
completable

## Desired State
Some state.

## Rationale
Some reason.

## Turn Configuration
### Evaluation Prompt
prompt

### Plan Sizing
sizing
"""

        result = parse_objective_definition("test", content)

        assert result.examples == []


class TestParseObjectiveNotes:
    """Tests for parse_objective_notes."""

    def test_parses_notes_with_timestamps(self) -> None:
        """Should parse notes with ISO timestamps."""
        content = """# Notes: cli-ensure-error-handling

## 2024-01-15T10:30:00Z
Found 15 files with direct exception patterns.
Most are in the wt/ command group.

## 2024-01-16T14:00:00Z
Completed first batch of migrations.
Remaining files are in plan/ command group.
"""

        result = parse_objective_notes(content)

        assert len(result.entries) == 2
        assert result.entries[0].timestamp == "2024-01-15T10:30:00Z"
        assert "15 files" in result.entries[0].content
        assert result.entries[1].timestamp == "2024-01-16T14:00:00Z"
        assert "plan/ command group" in result.entries[1].content

    def test_parses_notes_with_date_only_timestamps(self) -> None:
        """Should parse notes with date-only timestamps."""
        content = """# Notes: test

## 2024-01-15
First entry.

## 2024-01-16
Second entry.
"""

        result = parse_objective_notes(content)

        assert len(result.entries) == 2
        assert result.entries[0].timestamp == "2024-01-15"
        assert result.entries[1].timestamp == "2024-01-16"

    def test_parses_source_turn_metadata(self) -> None:
        """Should extract source_turn from note content."""
        content = """# Notes: test

## 2024-01-15T10:30:00Z
**Source Turn:** turn-123-abc

Found some interesting patterns.
"""

        result = parse_objective_notes(content)

        assert len(result.entries) == 1
        assert result.entries[0].source_turn == "turn-123-abc"
        assert "Found some interesting patterns" in result.entries[0].content
        assert "Source Turn" not in result.entries[0].content

    def test_handles_empty_notes(self) -> None:
        """Should return empty entries for empty content."""
        content = """# Notes: test

No entries yet.
"""

        result = parse_objective_notes(content)

        assert len(result.entries) == 0

    def test_handles_notes_with_code_blocks(self) -> None:
        """Should handle notes containing code blocks."""
        content = """# Notes: test

## 2024-01-15T10:30:00Z
Example pattern found:

```python
try:
    do_something()
except Exception:
    pass
```

Should be migrated.
"""

        result = parse_objective_notes(content)

        assert len(result.entries) == 1
        assert "```python" in result.entries[0].content
        assert "do_something()" in result.entries[0].content
