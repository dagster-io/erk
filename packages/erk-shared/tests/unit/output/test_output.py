"""Tests for output utilities."""

from io import StringIO
from unittest.mock import patch

from erk_shared.output.output import user_confirm


class TestUserConfirm:
    """Tests for user_confirm function."""

    def test_user_confirm_flushes_stderr_before_prompting(self) -> None:
        """Verify stderr is flushed before click.confirm is called."""
        flush_called_before_confirm = False

        def track_flush() -> None:
            nonlocal flush_called_before_confirm
            flush_called_before_confirm = True

        def mock_confirm(prompt: str, default: bool, err: bool) -> bool:
            # Check that flush was called before we got here
            flush_err = "stderr.flush() must be called before click.confirm()"
            assert flush_called_before_confirm, flush_err
            return True

        with (
            patch("sys.stderr", new_callable=StringIO) as mock_stderr,
            patch("erk_shared.output.output.click.confirm", side_effect=mock_confirm),
        ):
            mock_stderr.flush = track_flush  # type: ignore[method-assign]
            result = user_confirm("Continue?")

        assert result is True

    def test_user_confirm_returns_true_on_confirmation(self) -> None:
        """Verify user_confirm returns True when user confirms."""
        with patch("erk_shared.output.output.click.confirm", return_value=True):
            assert user_confirm("Continue?") is True

    def test_user_confirm_returns_false_on_rejection(self) -> None:
        """Verify user_confirm returns False when user rejects."""
        with patch("erk_shared.output.output.click.confirm", return_value=False):
            assert user_confirm("Continue?") is False

    def test_user_confirm_passes_correct_arguments(self) -> None:
        """Verify user_confirm passes default=False and err=True to click.confirm."""
        with patch("erk_shared.output.output.click.confirm", return_value=True) as mock_confirm:
            user_confirm("Are you sure?")

        mock_confirm.assert_called_once_with("Are you sure?", default=False, err=True)
