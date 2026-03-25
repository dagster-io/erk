"""Classify PR review feedback mechanically before LLM processing.

This command handles deterministic classification of PR review feedback:
- Data fetching (reviews, threads, discussion comments)
- Bot detection ([bot] suffix)
- Mechanical classification (APPROVED → informational, CHANGES_REQUESTED → actionable)
- Restructuring detection (renamed/moved files)
- Pre-existing issue candidate flagging

The LLM (pr-feedback-classifier skill) only handles:
- Action summaries
- Complexity estimation
- Ambiguous review classification
- Batch construction

Usage:
    erk exec classify-pr-feedback
    erk exec classify-pr-feedback --pr 123
    erk exec classify-pr-feedback --include-resolved

Output:
    JSON with mechanically classified feedback (intermediate format for LLM)

Exit Codes:
    0: Success (or graceful error with JSON output)
    1: Context not initialized
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import click

from erk.cli.script_output import exit_with_error
from erk_shared.context.helpers import (
    get_current_branch,
    require_git,
    require_github,
    require_issues,
    require_repo_root,
)
from erk_shared.gateway.git.abc import Git
from erk_shared.gateway.github.checks import GitHubChecks
from erk_shared.gateway.github.issues.types import IssueComment
from erk_shared.gateway.github.types import PRReview, PRReviewThread
from erk_shared.non_ideal_state import BranchDetectionFailed
from erk_shared.subprocess_utils import run_subprocess_with_context

# --- Frozen dataclasses for output ---


@dataclass(frozen=True)
class RestructuredFile:
    """A file that was renamed, copied, or moved in the PR."""

    old_path: str
    new_path: str
    status: str  # R100, R085, C100, etc.


@dataclass(frozen=True)
class ClassifiedReview:
    """A PR-level review submission with mechanical classification."""

    id: str
    author: str
    state: str
    body_preview: str  # First 200 chars
    classification: Literal["actionable", "informational", "needs_llm"]
    is_bot: bool


@dataclass(frozen=True)
class ClassifiedThread:
    """A review thread with mechanical pre-existing detection."""

    thread_id: str
    path: str
    line: int | None
    is_outdated: bool
    author: str
    comment_preview: str  # First 200 chars
    is_bot: bool
    pre_existing_candidate: bool


@dataclass(frozen=True)
class ClassifiedDiscussionComment:
    """A discussion comment with mechanical classification."""

    comment_id: int
    author: str
    body_preview: str  # First 200 chars
    classification: Literal["informational", "needs_llm"]
    is_bot: bool


@dataclass(frozen=True)
class ClassificationResult:
    """Complete classification result with intermediate format for LLM."""

    success: bool
    pr_number: int
    pr_title: str
    pr_url: str
    review_submissions: tuple[ClassifiedReview, ...]
    review_threads: tuple[ClassifiedThread, ...]
    discussion_comments: tuple[ClassifiedDiscussionComment, ...]
    restructured_files: tuple[RestructuredFile, ...]
    mechanical_informational_count: int
    error: str | None


# --- Helper functions ---


def _parse_name_status_output(output: str) -> tuple[RestructuredFile, ...]:
    """Parse git diff --name-status output into restructured file records.

    Handles rename (R), copy (C), add (A), modify (M), delete (D) statuses.
    Only returns R and C entries (restructuring candidates).

    Examples:
        R100    old/path.py    new/path.py
        R085    src/old.py     src/new.py
        C100    base.py        copy.py
        M       file.py
        A       new.py
        D       gone.py

    Args:
        output: Raw git diff --name-status -M -C output

    Returns:
        Tuple of RestructuredFile entries for R/C statuses only
    """
    if not output.strip():
        return ()

    restructured: list[RestructuredFile] = []
    for line in output.strip().split("\n"):
        parts = line.split("\t")
        if len(parts) < 2:
            continue

        status = parts[0]
        # Only care about renames (R) and copies (C)
        if not status.startswith("R") and not status.startswith("C"):
            continue

        # R/C have 3 parts: status, old_path, new_path
        if len(parts) != 3:
            continue

        restructured.append(
            RestructuredFile(
                old_path=parts[1],
                new_path=parts[2],
                status=status,
            )
        )

    return tuple(restructured)


def _is_bot(author: str) -> bool:
    """Check if author is a bot by [bot] suffix.

    Args:
        author: GitHub username

    Returns:
        True if author ends with [bot], False otherwise
    """
    return author.endswith("[bot]")


def _is_known_informational_discussion(author: str, body: str) -> bool:
    """Check if discussion comment is known informational (CI/Graphite bots).

    Patterns:
    - Graphite stack comments (Graphite Automations, graphite-app)
    - CI status updates (github-actions[bot])
    - PR description summaries

    Args:
        author: Comment author
        body: Comment body text

    Returns:
        True if known informational pattern, False otherwise
    """
    # Graphite stack comments
    if author in ("Graphite Automations", "graphite-app[bot]"):
        return True

    # CI status updates from github-actions
    if author == "github-actions[bot]":
        # Check for common CI update patterns
        ci_patterns = [
            "CI checks",
            "workflow",
            "Test results",
            "Build status",
        ]
        if any(pattern in body for pattern in ci_patterns):
            return True

    return False


def _classify_impl(
    *,
    reviews: list[PRReview],
    threads: list[PRReviewThread],
    comments: list[IssueComment],
    restructured_files: tuple[RestructuredFile, ...],
) -> ClassificationResult:
    """Core classification logic (pure function for testing).

    Applies mechanical classification rules:
    - APPROVED reviews → informational
    - CHANGES_REQUESTED reviews → actionable
    - COMMENTED reviews with empty body → informational
    - COMMENTED reviews with body → needs_llm
    - Bot + restructured path → pre_existing_candidate
    - Known informational discussion → informational

    Args:
        reviews: PR-level review submissions
        threads: Review threads
        comments: Discussion comments
        restructured_files: Renamed/moved files from git diff

    Returns:
        ClassificationResult with mechanically classified items
    """
    classified_reviews: list[ClassifiedReview] = []
    classified_threads: list[ClassifiedThread] = []
    classified_discussion: list[ClassifiedDiscussionComment] = []
    mechanical_informational_count = 0

    # Classify PR-level reviews
    for review in reviews:
        is_bot = _is_bot(review.author)
        body_preview = review.body[:200] if review.body else ""

        # APPROVED → informational (not actionable)
        if review.state == "APPROVED":
            mechanical_informational_count += 1
            continue  # Don't add to review_submissions

        # CHANGES_REQUESTED → always actionable
        if review.state == "CHANGES_REQUESTED":
            classified_reviews.append(
                ClassifiedReview(
                    id=review.id,
                    author=review.author,
                    state=review.state,
                    body_preview=body_preview,
                    classification="actionable",
                    is_bot=is_bot,
                )
            )
            continue

        # COMMENTED with empty body → informational
        if review.state == "COMMENTED" and not review.body:
            mechanical_informational_count += 1
            continue

        # COMMENTED with body → needs LLM judgment
        if review.state == "COMMENTED":
            classified_reviews.append(
                ClassifiedReview(
                    id=review.id,
                    author=review.author,
                    state=review.state,
                    body_preview=body_preview,
                    classification="needs_llm",
                    is_bot=is_bot,
                )
            )

    # Classify review threads
    restructured_paths = {f.new_path for f in restructured_files}
    for thread in threads:
        if not thread.comments:
            continue

        first_comment = thread.comments[0]
        is_bot = _is_bot(first_comment.author)
        comment_preview = first_comment.body[:200] if first_comment.body else ""

        # Check if thread is on a restructured file (bot + restructured → candidate)
        pre_existing_candidate = is_bot and thread.path in restructured_paths

        classified_threads.append(
            ClassifiedThread(
                thread_id=thread.id,
                path=thread.path,
                line=thread.line,
                is_outdated=thread.is_outdated,
                author=first_comment.author,
                comment_preview=comment_preview,
                is_bot=is_bot,
                pre_existing_candidate=pre_existing_candidate,
            )
        )

    # Classify discussion comments
    for comment in comments:
        is_bot = _is_bot(comment.author)
        body_preview = comment.body[:200] if comment.body else ""

        # Known informational patterns → informational
        if _is_known_informational_discussion(comment.author, comment.body):
            mechanical_informational_count += 1
            classified_discussion.append(
                ClassifiedDiscussionComment(
                    comment_id=comment.id,
                    author=comment.author,
                    body_preview=body_preview,
                    classification="informational",
                    is_bot=is_bot,
                )
            )
            continue

        # Unknown pattern → needs LLM
        classified_discussion.append(
            ClassifiedDiscussionComment(
                comment_id=comment.id,
                author=comment.author,
                body_preview=body_preview,
                classification="needs_llm",
                is_bot=is_bot,
            )
        )

    # Build result (no PR details needed, caller provides)
    return ClassificationResult(
        success=True,
        pr_number=0,  # Placeholder, filled by caller
        pr_title="",  # Placeholder, filled by caller
        pr_url="",  # Placeholder, filled by caller
        review_submissions=tuple(classified_reviews),
        review_threads=tuple(classified_threads),
        discussion_comments=tuple(classified_discussion),
        restructured_files=restructured_files,
        mechanical_informational_count=mechanical_informational_count,
        error=None,
    )


def _detect_trunk_branch(git: Git, repo_root: Path) -> str | None:
    """Detect trunk branch (main or master) by checking remote.

    Args:
        git: Git gateway
        repo_root: Repository root path

    Returns:
        Trunk branch name (main or master) or None if neither exists
    """
    for candidate in ["main", "master"]:
        if git.branch.branch_exists_on_remote(repo_root, "origin", candidate):
            return candidate
    return None


def _get_restructured_files(*, repo_root: Path, trunk: str) -> tuple[RestructuredFile, ...]:
    """Get renamed/moved files using git diff --name-status -M -C.

    Args:
        repo_root: Repository root path
        trunk: Trunk branch name (main or master)

    Returns:
        Tuple of RestructuredFile entries
    """
    try:
        result = run_subprocess_with_context(
            cmd=["git", "diff", "--name-status", "-M", "-C", f"{trunk}...HEAD"],
            operation_context=f"detect file restructuring against {trunk}",
            cwd=repo_root,
        )
        return _parse_name_status_output(result.stdout)
    except RuntimeError:
        # If git diff fails, return empty tuple (no restructuring detected)
        return ()


# --- CLI command ---


@click.command(name="classify-pr-feedback")
@click.option("--pr", type=int, default=None, help="PR number (defaults to current branch's PR)")
@click.option("--include-resolved", is_flag=True, help="Include resolved review threads")
@click.pass_context
def classify_pr_feedback(ctx: click.Context, pr: int | None, include_resolved: bool) -> None:
    """Classify PR review feedback mechanically before LLM processing.

    Fetches reviews, threads, and discussion comments, then applies deterministic
    classification rules. Output is an intermediate JSON format for the LLM to
    fill in semantic fields (action_summary, complexity, batches).

    If --pr is not specified, finds the PR for the current branch.
    """
    repo_root = require_repo_root(ctx)
    github = require_github(ctx)
    github_issues = require_issues(ctx)
    git = require_git(ctx)

    # Single PR lookup
    if pr is None:
        branch = GitHubChecks.branch(get_current_branch(ctx))
        if isinstance(branch, BranchDetectionFailed):
            branch.ensure()
        assert not isinstance(branch, BranchDetectionFailed)  # Type narrowing after NoReturn
        pr_details = GitHubChecks.pr_for_branch(github, repo_root, branch).ensure()
    else:
        pr_details = GitHubChecks.pr_by_number(github, repo_root, pr).ensure()

    # Detect trunk branch for restructuring analysis
    trunk = _detect_trunk_branch(git, repo_root)
    if trunk is None:
        # No trunk branch detected, skip restructuring analysis
        restructured_files: tuple[RestructuredFile, ...] = ()
    else:
        restructured_files = _get_restructured_files(repo_root=repo_root, trunk=trunk)

    # Parallel fetch of reviews, review threads, and discussion comments
    with ThreadPoolExecutor(max_workers=3) as executor:
        reviews_future = executor.submit(
            github.get_pr_reviews,
            repo_root,
            pr_details.number,
        )
        threads_future = executor.submit(
            github.get_pr_review_threads,
            repo_root,
            pr_details.number,
            include_resolved=include_resolved,
        )
        comments_future = executor.submit(
            GitHubChecks.issue_comments,
            github_issues,
            repo_root,
            pr_details.number,
        )

        reviews = reviews_future.result()

        try:
            threads = threads_future.result()
        except RuntimeError as e:
            exit_with_error("github-api-failed", str(e))

        issue_comments = comments_future.result().ensure()

    # Filter out threads with invalid IDs
    valid_threads = [t for t in threads if t.id]

    # Classify mechanically
    result = _classify_impl(
        reviews=reviews,
        threads=valid_threads,
        comments=list(issue_comments.comments),
        restructured_files=restructured_files,
    )

    # Fill in PR details from lookup
    final_result = ClassificationResult(
        success=result.success,
        pr_number=pr_details.number,
        pr_title=pr_details.title,
        pr_url=pr_details.url,
        review_submissions=result.review_submissions,
        review_threads=result.review_threads,
        discussion_comments=result.discussion_comments,
        restructured_files=result.restructured_files,
        mechanical_informational_count=result.mechanical_informational_count,
        error=result.error,
    )

    click.echo(json.dumps(asdict(final_result), indent=2))
    raise SystemExit(0)
