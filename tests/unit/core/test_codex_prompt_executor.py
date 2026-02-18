"""Tests for CodexPromptExecutor arg building and logic.

These tests verify the arg-building functions extracted for testability,
without requiring Codex CLI to be installed.
"""

from __future__ import annotations

from pathlib import Path

from erk.core.codex_prompt_executor import (
    build_codex_exec_args,
    build_codex_prompt_args,
    build_codex_tui_args,
)


class TestBuildCodexExecArgs:
    """Tests for build_codex_exec_args()."""

    def test_basic_args_with_json(self) -> None:
        result = build_codex_exec_args(
            prompt="hello",
            worktree_path=Path("/repo"),
            permission_mode="edits",
            json_output=True,
            model=None,
        )
        assert result == ["codex", "exec", "--json", "--cd", "/repo", "--full-auto", "hello"]

    def test_without_json(self) -> None:
        result = build_codex_exec_args(
            prompt="hello",
            worktree_path=Path("/repo"),
            permission_mode="edits",
            json_output=False,
            model=None,
        )
        assert result == ["codex", "exec", "--cd", "/repo", "--full-auto", "hello"]

    def test_with_model(self) -> None:
        result = build_codex_exec_args(
            prompt="hello",
            worktree_path=Path("/repo"),
            permission_mode="edits",
            json_output=True,
            model="o3",
        )
        assert "--model" in result
        model_idx = result.index("--model")
        assert result[model_idx + 1] == "o3"

    def test_safe_mode(self) -> None:
        result = build_codex_exec_args(
            prompt="hello",
            worktree_path=Path("/repo"),
            permission_mode="safe",
            json_output=True,
            model=None,
        )
        assert "--sandbox" in result
        sandbox_idx = result.index("--sandbox")
        assert result[sandbox_idx + 1] == "read-only"

    def test_dangerous_mode(self) -> None:
        result = build_codex_exec_args(
            prompt="hello",
            worktree_path=Path("/repo"),
            permission_mode="dangerous",
            json_output=True,
            model=None,
        )
        assert "--yolo" in result

    def test_plan_mode(self) -> None:
        result = build_codex_exec_args(
            prompt="hello",
            worktree_path=Path("/repo"),
            permission_mode="plan",
            json_output=True,
            model=None,
        )
        assert "--sandbox" in result
        sandbox_idx = result.index("--sandbox")
        assert result[sandbox_idx + 1] == "read-only"

    def test_prompt_is_last_arg(self) -> None:
        result = build_codex_exec_args(
            prompt="do something",
            worktree_path=Path("/repo"),
            permission_mode="edits",
            json_output=True,
            model="o3",
        )
        assert result[-1] == "do something"


class TestBuildCodexTuiArgs:
    """Tests for build_codex_tui_args()."""

    def test_basic_tui_args(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="edits",
            model=None,
            command="",
        )
        assert result[:1] == ["codex"]
        assert "--cd" in result
        cd_idx = result.index("--cd")
        assert result[cd_idx + 1] == "/repo"
        assert "--sandbox" in result
        assert "-a" in result

    def test_tui_with_model(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="edits",
            model="gpt-5",
            command="",
        )
        assert "--model" in result
        model_idx = result.index("--model")
        assert result[model_idx + 1] == "gpt-5"

    def test_tui_with_command(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="edits",
            model=None,
            command="implement this feature",
        )
        assert result[-1] == "implement this feature"

    def test_tui_empty_command_not_appended(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="edits",
            model=None,
            command="",
        )
        # Empty command should not be appended
        assert result[-1] != ""

    def test_tui_safe_mode_uses_untrusted(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="safe",
            model=None,
            command="",
        )
        assert "-a" in result
        a_idx = result.index("-a")
        assert result[a_idx + 1] == "untrusted"

    def test_tui_plan_mode_uses_never(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="plan",
            model=None,
            command="",
        )
        assert "-a" in result
        a_idx = result.index("-a")
        assert result[a_idx + 1] == "never"

    def test_tui_dangerous_mode(self) -> None:
        result = build_codex_tui_args(
            target_dir=Path("/repo"),
            permission_mode="dangerous",
            model=None,
            command="",
        )
        assert "--yolo" in result


class TestBuildCodexPromptArgs:
    """Tests for build_codex_prompt_args()."""

    def test_basic_prompt_args(self) -> None:
        result = build_codex_prompt_args(
            prompt="generate a commit message",
            cwd=Path("/repo"),
            permission_mode="edits",
            model="o3",
            output_file=Path("/tmp/out.txt"),
            system_prompt=None,
        )
        assert result[:2] == ["codex", "exec"]
        assert "--output-last-message" in result
        olm_idx = result.index("--output-last-message")
        assert result[olm_idx + 1] == "/tmp/out.txt"
        assert "--cd" in result
        assert "--model" in result
        assert result[-1] == "generate a commit message"

    def test_system_prompt_prepended(self) -> None:
        result = build_codex_prompt_args(
            prompt="user question",
            cwd=None,
            permission_mode="edits",
            model="o3",
            output_file=Path("/tmp/out.txt"),
            system_prompt="You are a helpful assistant.",
        )
        full_prompt = result[-1]
        assert full_prompt.startswith("<system>")
        assert "You are a helpful assistant." in full_prompt
        assert "user question" in full_prompt
        assert full_prompt.endswith("user question")

    def test_no_cd_when_cwd_is_none(self) -> None:
        result = build_codex_prompt_args(
            prompt="hello",
            cwd=None,
            permission_mode="edits",
            model="o3",
            output_file=Path("/tmp/out.txt"),
            system_prompt=None,
        )
        assert "--cd" not in result

    def test_dangerous_permission_mode(self) -> None:
        result = build_codex_prompt_args(
            prompt="hello",
            cwd=Path("/repo"),
            permission_mode="dangerous",
            model="o3",
            output_file=Path("/tmp/out.txt"),
            system_prompt=None,
        )
        assert "--yolo" in result


class TestCodexPromptExecutor:
    """Tests for CodexPromptExecutor methods that don't require subprocess."""

    def test_is_available_checks_codex_in_path(self) -> None:
        """Verify is_available uses shutil.which for codex."""
        from erk.core.codex_prompt_executor import CodexPromptExecutor

        executor = CodexPromptExecutor(console=None)
        # We just verify it returns a bool without error
        result = executor.is_available()
        assert isinstance(result, bool)
