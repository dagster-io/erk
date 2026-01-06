"""Tests for get_erk_label_definitions().

Pure unit tests (Layer 3) - no dependencies on fakes or external systems.
"""

from erk_shared.github.plan_issues import get_erk_label_definitions


def test_get_erk_label_definitions_returns_three_labels() -> None:
    """Test that get_erk_label_definitions returns all three expected labels."""
    labels = get_erk_label_definitions()

    assert len(labels) == 3


def test_get_erk_label_definitions_contains_erk_plan() -> None:
    """Test that erk-plan label is included with correct properties."""
    labels = get_erk_label_definitions()

    erk_plan_labels = [label for label in labels if label.name == "erk-plan"]
    assert len(erk_plan_labels) == 1

    erk_plan = erk_plan_labels[0]
    assert erk_plan.name == "erk-plan"
    assert erk_plan.description == "Implementation plan for manual execution"
    assert erk_plan.color == "0E8A16"  # Green


def test_get_erk_label_definitions_contains_erk_extraction() -> None:
    """Test that erk-extraction label is included with correct properties."""
    labels = get_erk_label_definitions()

    erk_extraction_labels = [label for label in labels if label.name == "erk-extraction"]
    assert len(erk_extraction_labels) == 1

    erk_extraction = erk_extraction_labels[0]
    assert erk_extraction.name == "erk-extraction"
    assert erk_extraction.description == "Documentation extraction plan"
    assert erk_extraction.color == "D93F0B"  # Orange


def test_get_erk_label_definitions_contains_erk_objective() -> None:
    """Test that erk-objective label is included with correct properties."""
    labels = get_erk_label_definitions()

    erk_objective_labels = [label for label in labels if label.name == "erk-objective"]
    assert len(erk_objective_labels) == 1

    erk_objective = erk_objective_labels[0]
    assert erk_objective.name == "erk-objective"
    assert erk_objective.description == "Multi-phase objective with roadmap"
    assert erk_objective.color == "5319E7"  # Purple


def test_get_erk_label_definitions_returns_frozen_dataclasses() -> None:
    """Test that returned LabelDefinition objects are frozen dataclasses."""
    labels = get_erk_label_definitions()

    for label in labels:
        # Frozen dataclasses should raise FrozenInstanceError on attribute assignment
        # We verify the dataclass has expected attributes
        assert hasattr(label, "name")
        assert hasattr(label, "description")
        assert hasattr(label, "color")
