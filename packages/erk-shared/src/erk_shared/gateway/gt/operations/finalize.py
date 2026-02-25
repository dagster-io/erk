"""Finalize utilities for submit-branch workflow.

Utility functions for finalize logic. The execute_finalize generator has
been replaced by the finalize_pr step in submit_pipeline.py.
"""

from pathlib import Path

from erk_shared.impl_folder import read_plan_ref

# Label added to PRs that originate from learn plans.
# Checked by land_cmd.py to skip creating pending-learn marker.
ERK_SKIP_LEARN_LABEL = "erk-skip-learn"


def is_learn_plan(impl_dir: Path) -> bool:
    """Check if the plan in the impl folder is a learn plan.

    Checks the labels stored in .impl/issue.json for the "erk-learn" label.

    Args:
        impl_dir: Path to .impl/ directory

    Returns:
        True if "erk-learn" label is present, False otherwise (including if
        issue.json doesn't exist or labels field is missing)
    """
    plan_ref = read_plan_ref(impl_dir)
    if plan_ref is None:
        return False

    return "erk-learn" in plan_ref.labels
