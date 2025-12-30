"""Unit tests for erk-user-prompt-hook.py."""

import json
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import by path since scripts/ is not a package
# We test the functions directly via exec
REPO_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))
from importlib.util import module_from_spec, spec_from_file_location  # noqa: E402

spec = spec_from_file_location(
    "erk_user_prompt_hook", REPO_ROOT / "scripts" / "erk-user-prompt-hook.py"
)
if spec is None or spec.loader is None:
    raise ImportError("Could not load erk-user-prompt-hook.py")
user_prompt_hook = module_from_spec(spec)
spec.loader.exec_module(user_prompt_hook)

# Direct function imports for cleaner tests
_get_repo_root = user_prompt_hook._get_repo_root
_is_in_managed_project = user_prompt_hook._is_in_managed_project
check_venv = user_prompt_hook.check_venv
persist_session_id = user_prompt_hook.persist_session_id
coding_standards_reminder = user_prompt_hook.coding_standards_reminder
tripwires_reminder = user_prompt_hook.tripwires_reminder


class TestGetRepoRoot:
    """Tests for _get_repo_root function."""

    def test_returns_path_when_in_git_repo(self, tmp_path: Path) -> None:
        """Test that function returns repo root when in git repo."""
        mock_result = MagicMock()
        mock_result.stdout = str(tmp_path) + "\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            result = _get_repo_root()

        mock_run.assert_called_once()
        assert result == tmp_path

    def test_returns_none_when_not_in_git_repo(self) -> None:
        """Test that function returns None when not in git repo."""
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(128, "git")
            result = _get_repo_root()

        assert result is None


class TestIsInManagedProject:
    """Tests for _is_in_managed_project function."""

    def test_returns_true_when_kits_toml_exists(self, tmp_path: Path) -> None:
        """Test returns True when .erk/kits.toml exists."""
        kits_file = tmp_path / ".erk" / "kits.toml"
        kits_file.parent.mkdir(parents=True)
        kits_file.write_text("# kits config", encoding="utf-8")

        result = _is_in_managed_project(tmp_path)

        assert result is True

    def test_returns_false_when_kits_toml_missing(self, tmp_path: Path) -> None:
        """Test returns False when .erk/kits.toml does not exist."""
        result = _is_in_managed_project(tmp_path)

        assert result is False


class TestCheckVenv:
    """Tests for check_venv function."""

    def test_no_block_when_venv_matches(self, tmp_path: Path) -> None:
        """Test no block when VIRTUAL_ENV matches expected .venv."""
        venv_path = tmp_path / ".venv"
        venv_path.mkdir()

        with patch.dict("os.environ", {"VIRTUAL_ENV": str(venv_path)}):
            should_block, message = check_venv(tmp_path, "test-session")

        assert should_block is False
        assert message == ""

    def test_no_block_when_no_venv_expected(self, tmp_path: Path) -> None:
        """Test no block when .venv directory doesn't exist."""
        # No .venv directory
        should_block, message = check_venv(tmp_path, "test-session")

        assert should_block is False
        assert message == ""

    def test_blocks_when_wrong_venv_activated(self, tmp_path: Path) -> None:
        """Test blocks when wrong venv is activated."""
        expected_venv = tmp_path / ".venv"
        expected_venv.mkdir()
        wrong_venv = tmp_path / "other-venv"
        wrong_venv.mkdir()

        with patch.dict("os.environ", {"VIRTUAL_ENV": str(wrong_venv)}):
            should_block, message = check_venv(tmp_path, "test-session")

        assert should_block is True
        assert "Wrong virtual environment" in message
        assert str(expected_venv.resolve()) in message

    def test_blocks_when_no_venv_activated_but_expected(self, tmp_path: Path) -> None:
        """Test blocks when no venv activated but .venv exists."""
        expected_venv = tmp_path / ".venv"
        expected_venv.mkdir()

        with patch.dict("os.environ", {}, clear=True):
            should_block, message = check_venv(tmp_path, "test-session")

        assert should_block is True
        assert "No virtual environment" in message

    def test_bypass_signal_skips_check(self, tmp_path: Path) -> None:
        """Test that bypass signal file allows bypassing venv check."""
        expected_venv = tmp_path / ".venv"
        expected_venv.mkdir()

        # Create bypass signal
        session_id = "bypass-session"
        bypass_signal = (
            tmp_path / ".erk" / "scratch" / "sessions" / session_id / "venv-bypass.signal"
        )
        bypass_signal.parent.mkdir(parents=True)
        bypass_signal.write_text("", encoding="utf-8")

        # Don't set VIRTUAL_ENV - would normally block
        with patch.dict("os.environ", {}, clear=True):
            should_block, message = check_venv(tmp_path, session_id)

        assert should_block is False


class TestPersistSessionId:
    """Tests for persist_session_id function."""

    def test_writes_session_id_to_file(self, tmp_path: Path) -> None:
        """Test that session ID is written to correct file."""
        session_id = "test-session-abc123"

        result = persist_session_id(tmp_path, session_id)

        session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
        assert session_file.exists()
        assert session_file.read_text(encoding="utf-8") == session_id
        assert f"📌 session: {session_id}" in result

    def test_creates_parent_directories(self, tmp_path: Path) -> None:
        """Test that parent directories are created if missing."""
        session_id = "test-session"

        persist_session_id(tmp_path, session_id)

        session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
        assert session_file.parent.exists()

    def test_returns_empty_for_unknown_session(self, tmp_path: Path) -> None:
        """Test that 'unknown' session returns empty string."""
        result = persist_session_id(tmp_path, "unknown")

        assert result == ""
        session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
        assert not session_file.exists()

    def test_overwrites_existing_file(self, tmp_path: Path) -> None:
        """Test that existing session file is overwritten."""
        session_file = tmp_path / ".erk" / "scratch" / "current-session-id"
        session_file.parent.mkdir(parents=True)
        session_file.write_text("old-session", encoding="utf-8")

        persist_session_id(tmp_path, "new-session")

        assert session_file.read_text(encoding="utf-8") == "new-session"


class TestCodingStandardsReminder:
    """Tests for coding_standards_reminder function."""

    def test_returns_expected_reminders(self) -> None:
        """Test that reminder includes key phrases."""
        result = coding_standards_reminder()

        assert "fake-driven-testing" in result
        assert "dignified-python" in result
        assert "NO try/except" in result
        assert "devrun" in result


class TestTripwiresReminder:
    """Tests for tripwires_reminder function."""

    def test_returns_tripwires_path(self) -> None:
        """Test that reminder mentions tripwires.md path."""
        result = tripwires_reminder()

        assert "tripwires.md" in result
        assert "docs/learned/tripwires.md" in result


class TestMainFunction:
    """Tests for main() function with various scenarios."""

    def test_exits_silently_when_not_in_git_repo(self) -> None:
        """Test silent exit when not in a git repo."""
        with patch.object(user_prompt_hook, "_get_repo_root", return_value=None):
            with patch.object(sys, "stdin", StringIO("")):
                # Should not raise or print anything
                user_prompt_hook.main()

    def test_exits_silently_when_not_managed_project(self, tmp_path: Path) -> None:
        """Test silent exit when not in a managed project."""
        with (
            patch.object(user_prompt_hook, "_get_repo_root", return_value=tmp_path),
            patch.object(user_prompt_hook, "_is_in_managed_project", return_value=False),
            patch.object(sys, "stdin", StringIO("")),
        ):
            user_prompt_hook.main()

    def test_blocks_on_venv_mismatch(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test exit code 2 and stderr output when venv check fails."""
        # Set up managed project
        (tmp_path / ".erk" / "kits.toml").parent.mkdir(parents=True)
        (tmp_path / ".erk" / "kits.toml").write_text("", encoding="utf-8")
        (tmp_path / ".venv").mkdir()

        stdin_data = json.dumps({"session_id": "test-session"})

        with (
            patch.object(user_prompt_hook, "_get_repo_root", return_value=tmp_path),
            patch.dict("os.environ", {}, clear=True),
            patch.object(sys, "stdin", StringIO(stdin_data)),
        ):
            with pytest.raises(SystemExit) as exc_info:
                user_prompt_hook.main()

        assert exc_info.value.code == 2
        captured = capsys.readouterr()
        assert "No virtual environment" in captured.err

    def test_outputs_all_context_when_checks_pass(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test stdout contains all context when all checks pass."""
        # Set up managed project with venv
        (tmp_path / ".erk" / "kits.toml").parent.mkdir(parents=True)
        (tmp_path / ".erk" / "kits.toml").write_text("", encoding="utf-8")
        venv_path = tmp_path / ".venv"
        venv_path.mkdir()

        session_id = "my-session-123"
        stdin_data = json.dumps({"session_id": session_id})

        with (
            patch.object(user_prompt_hook, "_get_repo_root", return_value=tmp_path),
            patch.dict("os.environ", {"VIRTUAL_ENV": str(venv_path)}),
            patch.object(sys, "stdin", StringIO(stdin_data)),
        ):
            user_prompt_hook.main()

        captured = capsys.readouterr()
        # Check all context parts are in output
        assert f"📌 session: {session_id}" in captured.out
        assert "fake-driven-testing" in captured.out
        assert "tripwires.md" in captured.out

    def test_handles_empty_stdin(self, tmp_path: Path) -> None:
        """Test graceful handling of empty stdin."""
        # Set up managed project with venv
        (tmp_path / ".erk" / "kits.toml").parent.mkdir(parents=True)
        (tmp_path / ".erk" / "kits.toml").write_text("", encoding="utf-8")
        venv_path = tmp_path / ".venv"
        venv_path.mkdir()

        with (
            patch.object(user_prompt_hook, "_get_repo_root", return_value=tmp_path),
            patch.dict("os.environ", {"VIRTUAL_ENV": str(venv_path)}),
            patch.object(sys, "stdin", StringIO("")),
        ):
            # Should not raise
            user_prompt_hook.main()
