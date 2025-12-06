"""Tests for CommitMessageGenerator."""

from pathlib import Path

from erk_shared.integrations.gt.events import CompletionEvent, ProgressEvent

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from tests.fakes.claude_executor import FakeClaudeExecutor


def _consume_generator(
    generator: CommitMessageGenerator, request: CommitMessageRequest
) -> tuple[CommitMessageResult, list[ProgressEvent]]:
    """Consume generator and return result with collected progress events."""
    progress_events: list[ProgressEvent] = []
    result: CommitMessageResult | None = None

    for event in generator.generate(request):
        if isinstance(event, ProgressEvent):
            progress_events.append(event)
        elif isinstance(event, CompletionEvent):
            result = event.result

    if result is None:
        raise AssertionError("Generator did not yield CompletionEvent")

    return result, progress_events


def test_generate_success(tmp_path: Path) -> None:
    """Test successful commit message generation."""
    # Arrange
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff --git a/file.py b/file.py\n-old\n+new", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Add new feature\n\nThis adds a new feature to the codebase.",
    )
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="feature-branch",
        parent_branch="main",
    )

    # Act
    result, progress_events = _consume_generator(generator, request)

    # Assert
    assert result.success is True
    assert result.title == "Add new feature"
    assert result.body == "This adds a new feature to the codebase."
    assert result.error_message is None

    # Verify progress events were emitted
    assert len(progress_events) >= 3  # Reading, loaded, analyzing, generated
    assert any("Reading diff" in e.message for e in progress_events)
    assert any("Analyzing" in e.message for e in progress_events)
    assert any(e.style == "success" for e in progress_events)

    # Verify prompt was called
    assert len(executor.prompt_calls) == 1
    assert "feature-branch" in executor.prompt_calls[0]
    assert "main" in executor.prompt_calls[0]


def test_generate_with_multiline_body(tmp_path: Path) -> None:
    """Test generation with multi-line body."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output=(
            "Refactor authentication module\n\n"
            "## Summary\n\n"
            "Restructured the auth module for better maintainability.\n\n"
            "## Files Changed\n\n"
            "- `auth.py` - Main changes\n"
            "- `tests/test_auth.py` - Updated tests"
        ),
    )
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="refactor",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Refactor authentication module"
    assert result.body is not None
    assert "## Summary" in result.body
    assert "## Files Changed" in result.body


def test_generate_fails_when_diff_file_not_found(tmp_path: Path) -> None:
    """Test that generation fails when diff file doesn't exist."""
    executor = FakeClaudeExecutor(claude_available=True)
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=tmp_path / "nonexistent.diff",
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is False
    assert result.title is None
    assert result.body is None
    assert result.error_message is not None
    assert "not found" in result.error_message.lower()

    # Verify no prompt was called
    assert len(executor.prompt_calls) == 0


def test_generate_fails_when_diff_file_empty(tmp_path: Path) -> None:
    """Test that generation fails when diff file is empty."""
    diff_file = tmp_path / "empty.diff"
    diff_file.write_text("", encoding="utf-8")

    executor = FakeClaudeExecutor(claude_available=True)
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is False
    assert result.error_message is not None
    assert "empty" in result.error_message.lower()

    # Verify no prompt was called
    assert len(executor.prompt_calls) == 0


def test_generate_fails_when_executor_fails(tmp_path: Path) -> None:
    """Test that generation fails when Claude execution fails."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_error="Claude CLI execution failed",
    )
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is False
    assert result.title is None
    assert result.body is None
    assert result.error_message is not None
    assert "failed" in result.error_message.lower()


def test_generate_handles_title_only_output(tmp_path: Path) -> None:
    """Test generation when output only has a title (no body)."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Fix typo in README",
    )
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="typo-fix",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Fix typo in README"
    assert result.body == ""


def test_generate_uses_custom_model(tmp_path: Path) -> None:
    """Test that custom model can be specified."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output="Title\n\nBody",
    )
    # Use sonnet instead of default haiku
    generator = CommitMessageGenerator(executor, model="sonnet")
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    # Should still work - model is passed to executor but FakeClaudeExecutor ignores it
    assert result.success is True


def test_generate_strips_code_fence_wrapper(tmp_path: Path) -> None:
    """Test that code fences wrapping the output are stripped."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    # Simulate Claude wrapping output in code fences
    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output=(
            "```\n"
            "Fix PR title parsing when Claude wraps output in code fences\n\n"
            "This fixes an issue where the parser would incorrectly use the code fence\n"
            "as the PR title when Claude wraps its response in markdown code blocks.\n"
            "```"
        ),
    )
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="fix-fence",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Fix PR title parsing when Claude wraps output in code fences"
    assert result.body is not None
    # Verify backticks are stripped (the content can mention "code fence" as words)
    assert "```" not in result.title


def test_generate_strips_code_fence_with_language_tag(tmp_path: Path) -> None:
    """Test that code fences with language tags (```markdown) are stripped."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    # Simulate Claude wrapping output in code fences with language specifier
    executor = FakeClaudeExecutor(
        claude_available=True,
        simulated_prompt_output=(
            "```markdown\nAdd new feature\n\n## Summary\n\nThis adds a new feature.\n```"
        ),
    )
    generator = CommitMessageGenerator(executor)
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="feature",
        parent_branch="main",
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Add new feature"
    assert result.body is not None
    assert "## Summary" in result.body
    assert "```" not in result.title
    assert "```" not in result.body
