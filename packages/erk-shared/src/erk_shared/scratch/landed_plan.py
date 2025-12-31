"""Scratch state module for landed plans linked to objectives.

This module provides functions to write and read landing state for plans
that are linked to objectives. This enables the objective-update skill
to know which plan was just landed and which objective to update.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from erk_shared.scratch.scratch import get_scratch_dir

_LANDED_PLAN_FILENAME = "last-landed-plan.json"


@dataclass(frozen=True)
class LandedPlanState:
    """State of a plan that was just landed.

    Written to scratch storage after a PR is merged so that the
    objective-update skill can access the context.

    Attributes:
        plan_issue: Issue number of the erk-plan that was just landed
        objective_issue: Issue number of the parent erk-objective
        pr_number: PR number that was merged
        pr_title: Title of the PR that was merged
    """

    plan_issue: int
    objective_issue: int
    pr_number: int
    pr_title: str


def write_landed_plan_state(
    session_id: str,
    state: LandedPlanState,
    *,
    repo_root: Path,
) -> Path:
    """Write landed plan state to scratch storage.

    Args:
        session_id: Claude session ID for isolation
        state: The landed plan state to write
        repo_root: Repository root directory

    Returns:
        Path to the written JSON file
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    file_path = scratch_dir / _LANDED_PLAN_FILENAME

    data = {
        "plan_issue": state.plan_issue,
        "objective_issue": state.objective_issue,
        "pr_number": state.pr_number,
        "pr_title": state.pr_title,
    }

    file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return file_path


def read_landed_plan_state(
    session_id: str,
    *,
    repo_root: Path,
) -> LandedPlanState | None:
    """Read landed plan state from scratch storage.

    Args:
        session_id: Claude session ID for isolation
        repo_root: Repository root directory

    Returns:
        LandedPlanState if file exists and is valid, None otherwise
    """
    scratch_dir = get_scratch_dir(session_id, repo_root=repo_root)
    file_path = scratch_dir / _LANDED_PLAN_FILENAME

    if not file_path.exists():
        return None

    content = file_path.read_text(encoding="utf-8")
    data = json.loads(content)

    return LandedPlanState(
        plan_issue=data["plan_issue"],
        objective_issue=data["objective_issue"],
        pr_number=data["pr_number"],
        pr_title=data["pr_title"],
    )
