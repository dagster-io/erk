"""Finalize utilities for submit-branch workflow.

Utility functions for finalize logic. The execute_finalize generator has
been replaced by the finalize_pr step in submit_pipeline.py.
"""

from pathlib import Path

from erk_shared.gateway.github.pr_footer import (
    ClosingReference,
    extract_closing_reference,
    extract_footer_from_body,
)
from erk_shared.gateway.github.types import PRNotFound
from erk_shared.gateway.gt.abc import GtKit
from erk_shared.impl_folder import read_issue_reference

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
    issue_ref = read_issue_reference(impl_dir)
    if issue_ref is None:
        return False

    return "erk-learn" in issue_ref.labels


def _extract_closing_ref_from_pr(
    ops: GtKit,
    cwd: Path,
    pr_number: int,
) -> ClosingReference | None:
    """Extract closing reference from an existing PR's footer.

    Used to preserve closing references when .impl/issue.json is missing.
    """
    repo_root = ops.git.repo.get_repository_root(cwd)
    current_pr = ops.github.get_pr(repo_root, pr_number)
    if isinstance(current_pr, PRNotFound) or not current_pr.body:
        return None
    existing_footer = extract_footer_from_body(current_pr.body)
    if existing_footer is None:
        return None
    return extract_closing_reference(existing_footer)
