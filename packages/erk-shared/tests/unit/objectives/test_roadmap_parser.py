# SPDX-License-Identifier: Apache-2.0
"""Tests for roadmap parser module."""

import dataclasses

import pytest

from erk_shared.objectives.roadmap_parser import (
    RoadmapParseResult,
    RoadmapStep,
    get_next_actionable_step,
    parse_roadmap_tables,
)


class TestParseRoadmapTables:
    """Tests for parse_roadmap_tables function."""

    def test_empty_body_returns_empty_result(self) -> None:
        """Empty body should return empty steps and no errors."""
        result = parse_roadmap_tables("")
        assert result == RoadmapParseResult(steps=(), errors=())

    def test_no_tables_returns_empty_result(self) -> None:
        """Body with no tables should return empty steps and no errors."""
        body = """# Objective Title

        Some description text without any tables.

        ## Section

        More text here.
        """
        result = parse_roadmap_tables(body)
        assert result.steps == ()
        assert result.errors == ()

    def test_simple_table_with_pending_steps(self) -> None:
        """Parse simple table with pending steps."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do first thing | pending | |
| 1.2  | Do second thing | pending | |
"""
        result = parse_roadmap_tables(body)
        assert len(result.steps) == 2
        assert result.steps[0] == RoadmapStep(
            step_id="1.1",
            description="Do first thing",
            status="pending",
            pr_number=None,
            plan_number=None,
        )
        assert result.steps[1] == RoadmapStep(
            step_id="1.2",
            description="Do second thing",
            status="pending",
            pr_number=None,
            plan_number=None,
        )

    def test_table_with_mixed_statuses(self) -> None:
        """Parse table with mixed statuses."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | First thing | done | #123 |
| 1.2  | Second thing | blocked | |
| 1.3  | Third thing | pending | |
"""
        result = parse_roadmap_tables(body)
        assert len(result.steps) == 3
        assert result.steps[0].status == "done"
        assert result.steps[0].pr_number == 123
        assert result.steps[1].status == "blocked"
        assert result.steps[2].status == "pending"


class TestPRColumnFormats:
    """Tests for PR column parsing formats."""

    def test_empty_pr_column_is_pending(self) -> None:
        """Empty PR column means pending status."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | | |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "pending"
        assert result.steps[0].pr_number is None
        assert result.steps[0].plan_number is None

    def test_pr_number_is_done(self) -> None:
        """PR number like #123 means done status."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | | #123 |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "done"
        assert result.steps[0].pr_number == 123
        assert result.steps[0].plan_number is None

    def test_plan_in_progress(self) -> None:
        """'plan #456' means plan-in-progress status."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | | plan #456 |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "plan-in-progress"
        assert result.steps[0].pr_number is None
        assert result.steps[0].plan_number == 456

    def test_plan_in_progress_case_insensitive(self) -> None:
        """'Plan #456' should also work (case insensitive)."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | | Plan #456 |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "plan-in-progress"
        assert result.steps[0].plan_number == 456

    def test_whitespace_in_pr_column_is_pending(self) -> None:
        """Whitespace-only PR column means pending."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | |   |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "pending"

    def test_malformed_pr_column_is_pending(self) -> None:
        """Malformed PR column (not matching patterns) is treated as pending."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | | some random text |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "pending"
        assert result.steps[0].pr_number is None


class TestStatusColumnOverride:
    """Tests for Status column overriding PR column inference."""

    def test_blocked_overrides_pr_column(self) -> None:
        """'blocked' in Status column overrides PR column inference."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | blocked | #123 |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "blocked"
        assert result.steps[0].pr_number is None

    def test_skipped_overrides_pr_column(self) -> None:
        """'skipped' in Status column overrides PR column inference."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | skipped | plan #456 |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "skipped"
        assert result.steps[0].plan_number is None

    def test_blocked_case_insensitive(self) -> None:
        """'Blocked' should also work (case insensitive)."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | Blocked | |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].status == "blocked"


class TestMultipleTables:
    """Tests for parsing objectives with multiple phase tables."""

    def test_multiple_phase_tables(self) -> None:
        """Parse objective with multiple phase tables."""
        body = """
## Phase 1

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Phase 1 step 1 | done | #100 |
| 1.2  | Phase 1 step 2 | pending | |

## Phase 2

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 2.1  | Phase 2 step 1 | pending | |
"""
        result = parse_roadmap_tables(body)
        assert len(result.steps) == 3
        assert result.steps[0].step_id == "1.1"
        assert result.steps[1].step_id == "1.2"
        assert result.steps[2].step_id == "2.1"

    def test_steps_in_document_order(self) -> None:
        """Steps should be returned in document order."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1A.1 | First | pending | |
| 1A.2 | Second | pending | |
| 1B.1 | Third | pending | |
"""
        result = parse_roadmap_tables(body)
        step_ids = [s.step_id for s in result.steps]
        assert step_ids == ["1A.1", "1A.2", "1B.1"]


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_table_without_step_column_ignored(self) -> None:
        """Tables without Step column should be ignored."""
        body = """
| Name | Value |
| ---- | ----- |
| foo  | bar   |

| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Do thing | pending | |
"""
        result = parse_roadmap_tables(body)
        assert len(result.steps) == 1
        assert result.steps[0].step_id == "1.1"

    def test_malformed_table_partial_parse(self) -> None:
        """Malformed table should parse what it can."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Good row | pending | |
|      | Missing step ID | pending | |
| 1.3  | Another good row | pending | |
"""
        result = parse_roadmap_tables(body)
        # Should skip the row with missing step ID
        step_ids = [s.step_id for s in result.steps]
        assert step_ids == ["1.1", "1.3"]

    def test_table_with_alignment_markers(self) -> None:
        """Tables with alignment markers should parse correctly."""
        body = """
| Step | Description | Status | PR |
|:-----|:------------|:------:|---:|
| 1.1  | Do thing | pending | |
"""
        result = parse_roadmap_tables(body)
        assert len(result.steps) == 1
        assert result.steps[0].step_id == "1.1"

    def test_step_ids_with_various_formats(self) -> None:
        """Various step ID formats should be preserved."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Standard | pending | |
| 1A.2 | With letter | pending | |
| 2    | Just number | pending | |
"""
        result = parse_roadmap_tables(body)
        step_ids = [s.step_id for s in result.steps]
        assert step_ids == ["1.1", "1A.2", "2"]

    def test_description_with_special_characters(self) -> None:
        """Descriptions with special characters should be preserved."""
        body = """
| Step | Description | Status | PR |
| ---- | ----------- | ------ | -- |
| 1.1  | Create `parse_roadmap_tables()` function | pending | |
"""
        result = parse_roadmap_tables(body)
        assert result.steps[0].description == "Create `parse_roadmap_tables()` function"


class TestGetNextActionableStep:
    """Tests for get_next_actionable_step function."""

    def test_empty_steps_returns_none(self) -> None:
        """Empty steps should return None."""
        result = get_next_actionable_step(())
        assert result is None

    def test_first_step_pending_returns_first(self) -> None:
        """If first step is pending, return it."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        assert result is not None
        assert result.step_id == "1.1"

    def test_first_done_second_pending_returns_second(self) -> None:
        """If first step is done and second is pending, return second."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="done",
                pr_number=100,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        assert result is not None
        assert result.step_id == "1.2"

    def test_first_plan_in_progress_returns_none(self) -> None:
        """If first step has plan-in-progress, return None (wait for plan)."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="plan-in-progress",
                pr_number=None,
                plan_number=456,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        assert result is None

    def test_all_done_returns_none(self) -> None:
        """If all steps are done, return None."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="done",
                pr_number=100,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="done",
                pr_number=101,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        assert result is None

    def test_blocked_step_skipped(self) -> None:
        """Blocked step should not be returned as actionable."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="done",
                pr_number=100,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="blocked",
                pr_number=None,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.3",
                description="Third",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        # Blocked step doesn't count as "done", so 1.3 is not actionable
        assert result is None

    def test_skipped_step_counts_as_done_for_next(self) -> None:
        """Skipped step should not make next step actionable (not done)."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="skipped",
                pr_number=None,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        # Skipped is not "done", so 1.2 is not actionable
        assert result is None

    def test_plan_in_progress_blocks_next(self) -> None:
        """Plan-in-progress step should block next steps."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="plan-in-progress",
                pr_number=None,
                plan_number=456,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        assert result is None

    def test_gap_in_sequence_finds_correct_step(self) -> None:
        """Correctly find next step with gap in sequence."""
        steps = (
            RoadmapStep(
                step_id="1.1",
                description="First",
                status="done",
                pr_number=100,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.2",
                description="Second",
                status="done",
                pr_number=101,
                plan_number=None,
            ),
            RoadmapStep(
                step_id="1.3",
                description="Third",
                status="pending",
                pr_number=None,
                plan_number=None,
            ),
        )
        result = get_next_actionable_step(steps)
        assert result is not None
        assert result.step_id == "1.3"


class TestRoadmapStepDataclass:
    """Tests for RoadmapStep dataclass properties."""

    def test_roadmap_step_is_frozen(self) -> None:
        """RoadmapStep should be immutable (frozen)."""
        step = RoadmapStep(
            step_id="1.1",
            description="Test",
            status="pending",
            pr_number=None,
            plan_number=None,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            step.step_id = "2.1"  # type: ignore[misc]

    def test_roadmap_parse_result_is_frozen(self) -> None:
        """RoadmapParseResult should be immutable (frozen)."""
        result = RoadmapParseResult(steps=(), errors=())
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.steps = ()  # type: ignore[misc]


class TestRealWorldObjective:
    """Test with realistic objective body content."""

    def test_real_objective_format(self) -> None:
        """Parse realistic objective body."""
        body = """# Objective: Implement Reconciliation Loop

## Overview

This objective tracks the implementation of the reconciliation loop feature.

## Phase 1: Foundation

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 1.1 | Create roadmap parser | done | #5935 |
| 1.2 | Add step readiness detection | done | #5936 |
| 1.3 | Implement reconciler service | pending | |
| 1.4 | Add CLI integration | pending | |

## Phase 2: Advanced Features

| Step | Description | Status | PR |
|------|-------------|--------|-----|
| 2.1 | Add parallel execution | pending | |
| 2.2 | Implement rollback support | blocked | |

## Notes

Some additional notes about the objective.
"""
        result = parse_roadmap_tables(body)
        assert len(result.steps) == 6
        assert result.errors == ()

        # Verify Phase 1 steps
        assert result.steps[0].step_id == "1.1"
        assert result.steps[0].status == "done"
        assert result.steps[0].pr_number == 5935
        assert result.steps[1].step_id == "1.2"
        assert result.steps[1].status == "done"
        assert result.steps[2].step_id == "1.3"
        assert result.steps[2].status == "pending"

        # Verify Phase 2 steps
        assert result.steps[4].step_id == "2.1"
        assert result.steps[4].status == "pending"
        assert result.steps[5].step_id == "2.2"
        assert result.steps[5].status == "blocked"

        # Next actionable should be 1.3 (first pending after done)
        next_step = get_next_actionable_step(result.steps)
        assert next_step is not None
        assert next_step.step_id == "1.3"
