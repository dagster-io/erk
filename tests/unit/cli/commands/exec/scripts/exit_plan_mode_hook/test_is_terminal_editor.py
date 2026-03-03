"""Tests for the pure is_terminal_editor() function."""

from erk.cli.commands.exec.scripts.exit_plan_mode_hook import is_terminal_editor


class TestIsTerminalEditor:
    """Tests for the pure is_terminal_editor() function."""

    def test_vim_is_terminal_editor(self) -> None:
        """vim is recognized as terminal editor."""
        assert is_terminal_editor("vim") is True

    def test_nvim_is_terminal_editor(self) -> None:
        """nvim is recognized as terminal editor."""
        assert is_terminal_editor("nvim") is True

    def test_nano_is_terminal_editor(self) -> None:
        """nano is recognized as terminal editor."""
        assert is_terminal_editor("nano") is True

    def test_emacs_is_terminal_editor(self) -> None:
        """emacs is recognized as terminal editor."""
        assert is_terminal_editor("emacs") is True

    def test_vi_is_terminal_editor(self) -> None:
        """vi is recognized as terminal editor."""
        assert is_terminal_editor("vi") is True

    def test_code_is_not_terminal_editor(self) -> None:
        """code (VS Code) is not a terminal editor."""
        assert is_terminal_editor("code") is False

    def test_sublime_is_not_terminal_editor(self) -> None:
        """subl (Sublime Text) is not a terminal editor."""
        assert is_terminal_editor("subl") is False

    def test_none_is_not_terminal_editor(self) -> None:
        """None returns False."""
        assert is_terminal_editor(None) is False

    def test_full_path_vim_is_terminal_editor(self) -> None:
        """Full path like /usr/bin/vim is recognized as terminal editor."""
        assert is_terminal_editor("/usr/bin/vim") is True

    def test_full_path_nvim_is_terminal_editor(self) -> None:
        """Full path like /opt/homebrew/bin/nvim is recognized as terminal editor."""
        assert is_terminal_editor("/opt/homebrew/bin/nvim") is True

    def test_full_path_code_is_not_terminal_editor(self) -> None:
        """Full path like /usr/local/bin/code is not a terminal editor."""
        assert is_terminal_editor("/usr/local/bin/code") is False
