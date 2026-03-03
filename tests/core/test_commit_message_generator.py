"""Tests for CommitMessageGenerator."""

from pathlib import Path

from erk.core.commit_message_generator import (
    CommitMessageGenerator,
    CommitMessageRequest,
    CommitMessageResult,
)
from erk.core.plan_context_provider import PlanContext
from erk_shared.core.llm_caller import LlmCaller, LlmCallFailed, LlmResponse, NoApiKey
from erk_shared.gateway.gt.events import CompletionEvent, ProgressEvent
from erk_shared.gateway.time.fake import FakeTime


class RecordingLlmCaller(LlmCaller):
    """LlmCaller that records calls and returns a configured response."""

    def __init__(self, response: LlmResponse | NoApiKey | LlmCallFailed) -> None:
        self._response = response
        self.calls: list[tuple[str, str, int]] = []

    def call(
        self, prompt: str, *, system_prompt: str, max_tokens: int = 50
    ) -> LlmResponse | NoApiKey | LlmCallFailed:
        self.calls.append((prompt, system_prompt, max_tokens))
        return self._response


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

    caller = RecordingLlmCaller(
        LlmResponse(text="Add new feature\n\nThis adds a new feature to the codebase.")
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="feature-branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
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

    # Verify call was made
    assert len(caller.calls) == 1
    prompt, system_prompt, max_tokens = caller.calls[0]
    assert "feature-branch" in prompt
    assert "main" in prompt
    assert max_tokens == 4096


def test_generate_with_multiline_body(tmp_path: Path) -> None:
    """Test generation with multi-line body."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    caller = RecordingLlmCaller(
        LlmResponse(
            text=(
                "Refactor authentication module\n\n"
                "## Summary\n\n"
                "Restructured the auth module for better maintainability.\n\n"
                "## Files Changed\n\n"
                "- `auth.py` - Main changes\n"
                "- `tests/test_auth.py` - Updated tests"
            )
        )
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="refactor",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Refactor authentication module"
    assert result.body is not None
    assert "## Summary" in result.body
    assert "## Files Changed" in result.body


def test_generate_fails_when_diff_file_not_found(tmp_path: Path) -> None:
    """Test that generation fails when diff file doesn't exist."""
    caller = RecordingLlmCaller(LlmResponse(text="Title"))
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=tmp_path / "nonexistent.diff",
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is False
    assert result.title is None
    assert result.body is None
    assert result.error_message is not None
    assert "not found" in result.error_message.lower()

    # Verify no LLM call was made
    assert len(caller.calls) == 0


def test_generate_fails_when_diff_file_empty(tmp_path: Path) -> None:
    """Test that generation fails when diff file is empty."""
    diff_file = tmp_path / "empty.diff"
    diff_file.write_text("", encoding="utf-8")

    caller = RecordingLlmCaller(LlmResponse(text="Title"))
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is False
    assert result.error_message is not None
    assert "empty" in result.error_message.lower()

    # Verify no LLM call was made
    assert len(caller.calls) == 0


def test_generate_fails_when_no_api_key(tmp_path: Path) -> None:
    """Test that generation fails when API key is missing."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    caller = RecordingLlmCaller(NoApiKey(message="ANTHROPIC_API_KEY not set"))
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is False
    assert result.title is None
    assert result.body is None
    assert result.error_message is not None
    assert "ANTHROPIC_API_KEY" in result.error_message


def test_generate_fails_when_llm_call_fails(tmp_path: Path) -> None:
    """Test that generation fails when LLM call fails."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    caller = RecordingLlmCaller(LlmCallFailed(message="API timeout"))
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
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

    caller = RecordingLlmCaller(LlmResponse(text="Fix typo in README"))
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="typo-fix",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Fix typo in README"
    assert result.body == ""


def test_generate_strips_code_fence_wrapper(tmp_path: Path) -> None:
    """Test that code fences wrapping the output are stripped."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    caller = RecordingLlmCaller(
        LlmResponse(
            text=(
                "```\n"
                "Fix PR title parsing when Claude wraps output in code fences\n\n"
                "This fixes an issue where the parser would incorrectly use the code fence\n"
                "as the PR title when Claude wraps its response in markdown code blocks.\n"
                "```"
            )
        )
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="fix-fence",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Fix PR title parsing when Claude wraps output in code fences"
    assert result.body is not None
    assert "```" not in result.title


def test_generate_strips_code_fence_with_language_tag(tmp_path: Path) -> None:
    """Test that code fences with language tags (```markdown) are stripped."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    caller = RecordingLlmCaller(
        LlmResponse(
            text="```markdown\nAdd new feature\n\n## Summary\n\nThis adds a new feature.\n```"
        )
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="feature",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert result.title == "Add new feature"
    assert result.body is not None
    assert "## Summary" in result.body
    assert "```" not in result.title
    assert "```" not in result.body


def test_generate_includes_commit_messages_in_prompt(tmp_path: Path) -> None:
    """Test that commit messages are included in the prompt when provided."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff --git a/file.py b/file.py\n-old\n+new", encoding="utf-8")

    caller = RecordingLlmCaller(
        LlmResponse(text="Add feature based on commit context\n\nUsed commit messages.")
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="feature-branch",
        parent_branch="main",
        commit_messages=[
            "Initial implementation\n\nAdded basic structure.",
            "Fix bug in parsing\n\nFixed edge case in parser.",
        ],
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert len(caller.calls) == 1
    prompt, system_prompt, _max_tokens = caller.calls[0]
    assert "Initial implementation" in prompt
    assert "Added basic structure" in prompt
    assert "Fix bug in parsing" in prompt
    assert "Fixed edge case in parser" in prompt
    assert "Developer's Commit Messages" in prompt


def test_generate_works_without_commit_messages(tmp_path: Path) -> None:
    """Test that generation works when commit_messages is None."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    caller = RecordingLlmCaller(LlmResponse(text="Simple title\n\nSimple body."))
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert len(caller.calls) == 1
    prompt, system_prompt, _max_tokens = caller.calls[0]
    assert "Developer's Commit Messages" not in prompt


def test_generate_passes_system_prompt_separately(tmp_path: Path) -> None:
    """Test that system prompt is passed separately from user prompt."""
    from erk_shared.gateway.gt.prompts import COMMIT_MESSAGE_SYSTEM_PROMPT

    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff --git a/file.py b/file.py\n-old\n+new", encoding="utf-8")

    caller = RecordingLlmCaller(
        LlmResponse(text="Add new feature\n\nThis adds a new feature.")
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="feature-branch",
        parent_branch="main",
        commit_messages=None,
        plan_context=None,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True

    assert len(caller.calls) == 1
    prompt, system_prompt, _max_tokens = caller.calls[0]

    # System prompt should be passed separately
    assert system_prompt is not None
    assert system_prompt == COMMIT_MESSAGE_SYSTEM_PROMPT

    # User prompt should NOT contain the system prompt text
    assert COMMIT_MESSAGE_SYSTEM_PROMPT not in prompt

    # User prompt should still contain context and diff
    assert "feature-branch" in prompt
    assert "main" in prompt
    assert "diff --git" in prompt


def test_generate_includes_plan_context_in_prompt(tmp_path: Path) -> None:
    """Test that plan context is included in the prompt when provided."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff --git a/file.py b/file.py\n-old\n+new", encoding="utf-8")

    plan_context = PlanContext(
        plan_id="123",
        plan_content="# Plan: Fix Authentication Bug\n\nFix session expiration.",
        objective_summary=None,
    )

    caller = RecordingLlmCaller(
        LlmResponse(text="Fix authentication session expiration\n\nImplemented fix.")
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="P123-fix-auth",
        parent_branch="main",
        commit_messages=None,
        plan_context=plan_context,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert len(caller.calls) == 1
    prompt, _, _ = caller.calls[0]
    assert "Implementation Plan (Plan #123)" in prompt
    assert "Fix Authentication Bug" in prompt
    assert "session expiration" in prompt
    assert "primary source of truth" in prompt


def test_generate_includes_plan_context_with_objective_summary(tmp_path: Path) -> None:
    """Test that objective summary is included when present in plan context."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    plan_context = PlanContext(
        plan_id="456",
        plan_content="# Plan: Add Metrics\n\nAdd usage metrics tracking.",
        objective_summary="Objective #100: Improve Observability",
    )

    caller = RecordingLlmCaller(
        LlmResponse(text="Add usage metrics tracking\n\nImplemented metrics.")
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="P456-add-metrics",
        parent_branch="main",
        commit_messages=None,
        plan_context=plan_context,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert len(caller.calls) == 1
    prompt, _, _ = caller.calls[0]
    assert "Implementation Plan (Plan #456)" in prompt
    assert "Parent Objective" in prompt
    assert "Objective #100: Improve Observability" in prompt


def test_generate_includes_both_plan_and_commit_messages(tmp_path: Path) -> None:
    """Test that both plan context and commit messages are included when provided."""
    diff_file = tmp_path / "test.diff"
    diff_file.write_text("diff content", encoding="utf-8")

    plan_context = PlanContext(
        plan_id="789",
        plan_content="# Plan: Refactor API\n\nSimplify the API layer.",
        objective_summary=None,
    )

    caller = RecordingLlmCaller(
        LlmResponse(text="Refactor API for simplicity\n\nSimplified API layer.")
    )
    generator = CommitMessageGenerator(caller, time=FakeTime())
    request = CommitMessageRequest(
        diff_file=diff_file,
        repo_root=tmp_path,
        current_branch="P789-refactor-api",
        parent_branch="main",
        commit_messages=[
            "WIP: Started refactoring",
            "WIP: Continued work",
        ],
        plan_context=plan_context,
    )

    result, _ = _consume_generator(generator, request)

    assert result.success is True
    assert len(caller.calls) == 1
    prompt, _, _ = caller.calls[0]
    # Both should be present
    assert "Implementation Plan (Plan #789)" in prompt
    assert "Refactor API" in prompt
    assert "Developer's Commit Messages" in prompt
    assert "WIP: Started refactoring" in prompt
