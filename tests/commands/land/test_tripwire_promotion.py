"""Tests for tripwire promotion in erk land command.

Tests the behavior when landing a learn plan PR that contains tripwire candidates:
- Learn plan with candidates -> extraction succeeds
- Non-learn plan -> no candidates (returns empty)
- No tripwire section -> no candidates
- Issue not found -> returns empty (fail-open)
- Force mode -> auto-promotes without prompting
- Target doc missing -> skips with warning
"""

from datetime import UTC, datetime
from pathlib import Path

from erk.cli.commands.tripwire_promotion_helpers import (
    extract_tripwire_candidates_from_learn_plan,
    prompt_tripwire_promotion,
)
from erk_shared.context.context import ErkContext
from erk_shared.github.issues.fake import FakeGitHubIssues
from erk_shared.github.issues.types import IssueInfo
from erk_shared.github.metadata.plan_header import format_plan_content_comment
from erk_shared.learn.tripwire_candidates import TripwireCandidate


def _make_learn_plan_issue(
    number: int,
    plan_content: str,
) -> tuple[IssueInfo, dict[int, list[str]]]:
    """Create a learn plan issue with plan content in the first comment.

    Returns the issue and comments dict suitable for FakeGitHubIssues.
    """
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=number,
        title=f"[erk-learn] Learn plan #{number}",
        body="Plan metadata body",
        state="OPEN",
        url=f"https://github.com/test/repo/issues/{number}",
        labels=["erk-plan", "erk-learn"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    comment_body = format_plan_content_comment(plan_content)
    comments = {number: [comment_body]}
    return issue, comments


_PLAN_WITH_TRIPWIRES = """\
## Summary

Learn plan with tripwire candidates.

## Tripwire Additions

### For `architecture/foo.md`

```yaml
tripwires:
  - action: "calling foo() directly"
    warning: "Use the foo_wrapper() instead."
```

### For `cli/bar.md`

```yaml
tripwires:
  - action: "using bar without context"
    warning: "Pass ctx to bar()."
```
"""

_PLAN_WITHOUT_TRIPWIRES = """\
## Summary

Learn plan without tripwire candidates.

## Insights

Some insights about the codebase.
"""


def test_extract_candidates_from_learn_plan() -> None:
    """Extract tripwire candidates from a learn plan issue."""
    issue, comments = _make_learn_plan_issue(42, _PLAN_WITH_TRIPWIRES)
    fake_issues = FakeGitHubIssues(
        issues={42: issue},
        comments=comments,
    )
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=Path("/fake/repo"))

    candidates = extract_tripwire_candidates_from_learn_plan(
        ctx,
        repo_root=Path("/fake/repo"),
        plan_issue_number=42,
    )

    assert len(candidates) == 2
    assert candidates[0].action == "calling foo() directly"
    assert candidates[0].target_doc_path == "architecture/foo.md"
    assert candidates[1].action == "using bar without context"
    assert candidates[1].target_doc_path == "cli/bar.md"


def test_extract_candidates_non_learn_plan_returns_empty() -> None:
    """Return empty list for a non-learn plan (missing erk-learn label)."""
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=42,
        title="Regular plan",
        body="Plan body",
        state="OPEN",
        url="https://github.com/test/repo/issues/42",
        labels=["erk-plan"],  # No erk-learn
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    fake_issues = FakeGitHubIssues(issues={42: issue})
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=Path("/fake/repo"))

    candidates = extract_tripwire_candidates_from_learn_plan(
        ctx,
        repo_root=Path("/fake/repo"),
        plan_issue_number=42,
    )

    assert candidates == []


def test_extract_candidates_no_tripwire_section_returns_empty() -> None:
    """Return empty list when learn plan has no tripwire section."""
    issue, comments = _make_learn_plan_issue(42, _PLAN_WITHOUT_TRIPWIRES)
    fake_issues = FakeGitHubIssues(
        issues={42: issue},
        comments=comments,
    )
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=Path("/fake/repo"))

    candidates = extract_tripwire_candidates_from_learn_plan(
        ctx,
        repo_root=Path("/fake/repo"),
        plan_issue_number=42,
    )

    assert candidates == []


def test_extract_candidates_issue_not_found_returns_empty() -> None:
    """Return empty list when issue does not exist (fail-open)."""
    fake_issues = FakeGitHubIssues()
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=Path("/fake/repo"))

    candidates = extract_tripwire_candidates_from_learn_plan(
        ctx,
        repo_root=Path("/fake/repo"),
        plan_issue_number=999,
    )

    assert candidates == []


def test_extract_candidates_no_comments_returns_empty() -> None:
    """Return empty list when learn plan has no comments."""
    now = datetime.now(UTC)
    issue = IssueInfo(
        number=42,
        title="[erk-learn] Learn plan",
        body="Plan body",
        state="OPEN",
        url="https://github.com/test/repo/issues/42",
        labels=["erk-plan", "erk-learn"],
        assignees=[],
        created_at=now,
        updated_at=now,
        author="testuser",
    )
    fake_issues = FakeGitHubIssues(
        issues={42: issue},
        comments={42: []},  # No comments
    )
    ctx = ErkContext.for_test(github_issues=fake_issues, repo_root=Path("/fake/repo"))

    candidates = extract_tripwire_candidates_from_learn_plan(
        ctx,
        repo_root=Path("/fake/repo"),
        plan_issue_number=42,
    )

    assert candidates == []


def test_prompt_tripwire_promotion_force_mode(tmp_path: Path) -> None:
    """Force mode promotes tripwires without prompting."""
    doc_dir = tmp_path / "docs" / "learned" / "architecture"
    doc_dir.mkdir(parents=True)
    (doc_dir / "foo.md").write_text(
        "---\ntitle: Foo Patterns\n---\n\n# Foo Patterns\n",
        encoding="utf-8",
    )

    candidates = [
        TripwireCandidate(
            action="calling foo() directly",
            warning="Use the foo_wrapper() instead.",
            target_doc_path="architecture/foo.md",
        ),
    ]

    ctx = ErkContext.for_test(repo_root=tmp_path)

    prompt_tripwire_promotion(
        ctx,
        repo_root=tmp_path,
        candidates=candidates,
        force=True,
    )

    # Verify tripwire was added to frontmatter
    content = (doc_dir / "foo.md").read_text(encoding="utf-8")
    assert "calling foo() directly" in content
    assert "Use the foo_wrapper() instead." in content


def test_prompt_tripwire_promotion_target_doc_missing(tmp_path: Path) -> None:
    """Missing target doc results in warning but no crash (fail-open)."""
    candidates = [
        TripwireCandidate(
            action="calling missing()",
            warning="This doc does not exist.",
            target_doc_path="architecture/nonexistent.md",
        ),
    ]

    ctx = ErkContext.for_test(repo_root=tmp_path)

    # Should not raise - fail-open behavior
    prompt_tripwire_promotion(
        ctx,
        repo_root=tmp_path,
        candidates=candidates,
        force=True,
    )


def test_prompt_tripwire_promotion_empty_candidates(tmp_path: Path) -> None:
    """Empty candidates list results in no output or prompts."""
    ctx = ErkContext.for_test(repo_root=tmp_path)

    # Should be a no-op
    prompt_tripwire_promotion(
        ctx,
        repo_root=tmp_path,
        candidates=[],
        force=True,
    )
