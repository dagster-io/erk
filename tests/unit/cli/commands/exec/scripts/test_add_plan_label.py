"""Unit tests for add_plan_label exec command.

Tests backend-aware label addition using PlannedPRBackend and FakeLocalGitHub.
"""

import json
from pathlib import Path

from click.testing import CliRunner

from erk.cli.commands.exec.scripts.add_plan_label import add_plan_label
from erk_shared.context.testing import context_for_test
from erk_shared.fakes.github import FakeLocalGitHub
from erk_shared.fakes.time import FakeTime
from erk_shared.plan_store.planned_pr import PlannedPRBackend

# ============================================================================
# Success Cases
# ============================================================================


def test_add_plan_label_success() -> None:
    """Test successful label addition via PlannedPRBackend."""
    fake_github = FakeLocalGitHub()
    backend = PlannedPRBackend(fake_github, fake_github.issues, time=FakeTime())

    create_result = backend.create_plan(
        repo_root=Path("/repo"),
        title="Test Plan",
        content="Plan body",
        labels=("erk-plan",),
        metadata={"branch_name": "test-branch-label"},
        summary=None,
    )

    runner = CliRunner()
    result = runner.invoke(
        add_plan_label,
        [create_result.plan_id, "--label", "erk-consolidated"],
        obj=context_for_test(
            github=fake_github,
            plan_store=backend,
        ),
    )

    assert result.exit_code == 0
    output = json.loads(result.output)
    assert output["success"] is True
    assert output["plan_number"] == int(create_result.plan_id)
    assert output["label"] == "erk-consolidated"

    # Verify label was added via the fake GitHub PR label tracking
    assert (int(create_result.plan_id), "erk-consolidated") in fake_github._added_labels


# ============================================================================
# Error Cases
# ============================================================================


def test_add_plan_label_requires_label_flag() -> None:
    """Test that missing --label flag exits with code 2 (usage error)."""
    runner = CliRunner()

    result = runner.invoke(
        add_plan_label,
        ["42"],
        obj=context_for_test(),
    )

    assert result.exit_code == 2
