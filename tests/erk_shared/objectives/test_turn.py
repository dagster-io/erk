"""Tests for turn prompt building."""

from erk_shared.objectives.turn import (
    build_claude_prompt,
    build_turn_prompt,
    format_turn_output,
)
from erk_shared.objectives.types import (
    NoteEntry,
    ObjectiveDefinition,
    ObjectiveNotes,
    ObjectiveType,
)


class TestBuildTurnPrompt:
    """Tests for build_turn_prompt."""

    def test_builds_basic_prompt(self) -> None:
        """Should build prompt with objective definition."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="All tests pass.",
            rationale="Quality assurance.",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="Check test coverage.",
            plan_sizing_prompt="Fix 5 tests per plan.",
        )
        notes = ObjectiveNotes(entries=[])

        result = build_turn_prompt(definition, notes)

        assert result.objective_name == "test-objective"
        assert result.objective_type == ObjectiveType.COMPLETABLE
        assert "test-objective" in result.system_prompt
        assert "completable" in result.system_prompt
        assert "All tests pass" in result.system_prompt
        assert "Quality assurance" in result.system_prompt
        assert "Check test coverage" in result.user_prompt
        assert "Fix 5 tests per plan" in result.user_prompt

    def test_includes_scope_in_prompt(self) -> None:
        """Should include scope information in system prompt."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="Clean code.",
            rationale="Readability.",
            examples=[],
            scope_includes=["src/erk/", "src/erk_shared/"],
            scope_excludes=["tests/", "docs/"],
            evaluation_prompt="prompt",
            plan_sizing_prompt="sizing",
        )
        notes = ObjectiveNotes(entries=[])

        result = build_turn_prompt(definition, notes)

        assert "In Scope" in result.system_prompt
        assert "src/erk/" in result.system_prompt
        assert "src/erk_shared/" in result.system_prompt
        assert "Out of Scope" in result.system_prompt
        assert "tests/" in result.system_prompt
        assert "docs/" in result.system_prompt

    def test_includes_examples_in_prompt(self) -> None:
        """Should include examples in system prompt."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="Good patterns.",
            rationale="Best practices.",
            examples=["Before: x\nAfter: y"],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="prompt",
            plan_sizing_prompt="sizing",
        )
        notes = ObjectiveNotes(entries=[])

        result = build_turn_prompt(definition, notes)

        assert "Examples" in result.system_prompt
        assert "Before: x" in result.system_prompt
        assert "After: y" in result.system_prompt

    def test_includes_accumulated_notes(self) -> None:
        """Should include notes from previous turns."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="State.",
            rationale="Reason.",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="prompt",
            plan_sizing_prompt="sizing",
        )
        notes = ObjectiveNotes(
            entries=[
                NoteEntry(
                    timestamp="2024-01-15T10:30:00Z",
                    content="Found 5 files with issues.",
                    source_turn="turn-abc",
                ),
                NoteEntry(
                    timestamp="2024-01-16T14:00:00Z",
                    content="Fixed first batch.",
                ),
            ]
        )

        result = build_turn_prompt(definition, notes)

        assert "Accumulated Knowledge" in result.system_prompt
        assert "2024-01-15T10:30:00Z" in result.system_prompt
        assert "Found 5 files with issues" in result.system_prompt
        assert "turn-abc" in result.system_prompt
        assert "2024-01-16T14:00:00Z" in result.system_prompt
        assert "Fixed first batch" in result.system_prompt

    def test_user_prompt_contains_instructions(self) -> None:
        """Should include evaluation and response instructions."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="State.",
            rationale="Reason.",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="Check something.",
            plan_sizing_prompt="Small plans.",
        )
        notes = ObjectiveNotes(entries=[])

        result = build_turn_prompt(definition, notes)

        assert "Evaluation Task" in result.user_prompt
        assert "Check something" in result.user_prompt
        assert "Plan Sizing Guidelines" in result.user_prompt
        assert "Small plans" in result.user_prompt
        assert "STATUS: COMPLETE" in result.user_prompt
        assert "STATUS: GAPS_FOUND" in result.user_prompt


class TestFormatTurnOutput:
    """Tests for format_turn_output."""

    def test_formats_prompt_for_display(self) -> None:
        """Should format prompt in human-readable format."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.PERPETUAL,
            desired_state="State.",
            rationale="Reason.",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="prompt",
            plan_sizing_prompt="sizing",
        )
        notes = ObjectiveNotes(entries=[])
        prompt = build_turn_prompt(definition, notes)

        result = format_turn_output(prompt)

        assert "# Turn: test-objective" in result
        assert "Type: perpetual" in result
        assert "## System Prompt" in result
        assert "## User Prompt" in result


class TestBuildClaudePrompt:
    """Tests for build_claude_prompt."""

    def test_combines_system_and_user_prompts(self) -> None:
        """Should combine system and user prompts with separator."""
        definition = ObjectiveDefinition(
            name="test-objective",
            objective_type=ObjectiveType.COMPLETABLE,
            desired_state="All tests pass.",
            rationale="Quality assurance.",
            examples=[],
            scope_includes=[],
            scope_excludes=[],
            evaluation_prompt="Check test coverage.",
            plan_sizing_prompt="Fix 5 tests per plan.",
        )
        notes = ObjectiveNotes(entries=[])
        prompt = build_turn_prompt(definition, notes)

        result = build_claude_prompt(prompt)

        # Should contain system prompt content
        assert "test-objective" in result
        assert "All tests pass" in result
        assert "Quality assurance" in result

        # Should contain user prompt content
        assert "Check test coverage" in result
        assert "Fix 5 tests per plan" in result

        # Should have separator between system and user prompts
        assert "\n---\n" in result

    def test_preserves_prompt_structure(self) -> None:
        """Should preserve the structure of both prompts."""
        definition = ObjectiveDefinition(
            name="structured-test",
            objective_type=ObjectiveType.PERPETUAL,
            desired_state="Clean code.",
            rationale="Maintainability.",
            examples=["Example 1"],
            scope_includes=["src/"],
            scope_excludes=["tests/"],
            evaluation_prompt="Evaluate code quality.",
            plan_sizing_prompt="One file per plan.",
        )
        notes = ObjectiveNotes(
            entries=[
                NoteEntry(
                    timestamp="2024-01-15T10:30:00Z",
                    content="Previous finding.",
                )
            ]
        )
        prompt = build_turn_prompt(definition, notes)

        result = build_claude_prompt(prompt)

        # System prompt sections
        assert "Desired State" in result
        assert "Rationale" in result
        assert "In Scope" in result
        assert "Out of Scope" in result
        assert "Examples" in result
        assert "Accumulated Knowledge" in result

        # User prompt sections
        assert "Evaluation Task" in result
        assert "Plan Sizing Guidelines" in result
        assert "STATUS: COMPLETE" in result
        assert "STATUS: GAPS_FOUND" in result
