"""Resilient label addition using the GitHub gateway with retry."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from erk_shared.gateway.github.abc import GitHub
from erk_shared.gateway.github.retry import RetriesExhausted, RetryRequested, with_retries
from erk_shared.gateway.github.transient_errors import is_transient_error
from erk_shared.gateway.time.abc import Time

_logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AddLabelsResult:
    """Result from adding labels to a PR."""

    success: bool
    pr_number: int
    added_labels: list[str]
    failed_labels: list[str]
    errors: dict[str, str]


def add_labels_resilient(
    github: GitHub,
    *,
    time: Time,
    repo_root: Path,
    pr_number: int,
    labels: tuple[str, ...],
) -> AddLabelsResult:
    """Add labels to a PR with retry on transient errors. Never raises."""

    added: list[str] = []
    failed: dict[str, str] = {}

    for label in labels:

        def attempt(label: str = label) -> None | RetryRequested:
            try:
                github.add_label_to_pr(repo_root, pr_number, label)
                return None
            except RuntimeError as e:
                if is_transient_error(str(e)):
                    return RetryRequested(reason=str(e))
                raise

        try:
            result = with_retries(time, f"add label '{label}' to PR #{pr_number}", attempt)
            if isinstance(result, RetriesExhausted):
                failed[label] = result.reason
                _logger.warning(
                    "Failed to add label '%s' to PR #%d after retries: %s",
                    label,
                    pr_number,
                    result.reason,
                )
            else:
                added.append(label)
        except RuntimeError as e:
            failed[label] = str(e)
            _logger.warning("Failed to add label '%s' to PR #%d: %s", label, pr_number, e)

    return AddLabelsResult(
        success=len(failed) == 0,
        pr_number=pr_number,
        added_labels=added,
        failed_labels=list(failed.keys()),
        errors=failed,
    )
