"""Tests for CLI Ensure utility class."""

from unittest import mock

import pytest

from erk.cli.ensure import Ensure
from erk_shared.context.testing import context_for_test
from erk_shared.gateway.graphite.disabled import (
    GraphiteDisabled,
    GraphiteDisabledReason,
)


class TestEnsureNotNone:
    """Tests for Ensure.not_none method."""

    def test_returns_value_when_not_none(self) -> None:
        """Ensure.not_none returns the value unchanged when not None."""
        result = Ensure.not_none("hello", "Value is None")
        assert result == "hello"

    def test_returns_value_preserves_type(self) -> None:
        """Ensure.not_none preserves the type of the returned value."""
        value: int | None = 42
        result = Ensure.not_none(value, "Value is None")
        assert result == 42
        # Type checker should infer result as int, not int | None

    def test_exits_when_none(self) -> None:
        """Ensure.not_none raises SystemExit when value is None."""
        with pytest.raises(SystemExit) as exc_info:
            Ensure.not_none(None, "Value is None")
        assert exc_info.value.code == 1

    def test_error_message_output(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Ensure.not_none outputs error message with red Error prefix to stderr."""
        with pytest.raises(SystemExit):
            Ensure.not_none(None, "Custom error message")

        captured = capsys.readouterr()
        # user_output routes to stderr for shell integration
        assert "Error:" in captured.err
        assert "Custom error message" in captured.err

    def test_works_with_complex_types(self) -> None:
        """Ensure.not_none works with complex types like dicts and lists."""
        data: dict[str, int] | None = {"key": 123}
        result = Ensure.not_none(data, "Data is None")
        assert result == {"key": 123}

    def test_zero_is_not_none(self) -> None:
        """Ensure.not_none returns 0 since 0 is not None."""
        result = Ensure.not_none(0, "Value is None")
        assert result == 0

    def test_empty_string_is_not_none(self) -> None:
        """Ensure.not_none returns empty string since empty string is not None."""
        result = Ensure.not_none("", "Value is None")
        assert result == ""

    def test_empty_list_is_not_none(self) -> None:
        """Ensure.not_none returns empty list since empty list is not None."""
        result: list[str] | None = []
        actual = Ensure.not_none(result, "Value is None")
        assert actual == []

    def test_false_is_not_none(self) -> None:
        """Ensure.not_none returns False since False is not None."""
        result = Ensure.not_none(False, "Value is None")
        assert result is False


class TestEnsureGtInstalled:
    """Tests for Ensure.gt_installed method."""

    def test_succeeds_when_gt_on_path(self) -> None:
        """Ensure.gt_installed succeeds when gt is found on PATH."""
        with mock.patch("shutil.which", return_value="/usr/local/bin/gt"):
            # Should not raise
            Ensure.gt_installed()

    def test_exits_when_gt_not_found(self) -> None:
        """Ensure.gt_installed raises SystemExit when gt not on PATH."""
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                Ensure.gt_installed()

            assert exc_info.value.code == 1

    def test_error_message_includes_install_instructions(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Ensure.gt_installed outputs helpful installation instructions."""
        with mock.patch("shutil.which", return_value=None):
            with pytest.raises(SystemExit):
                Ensure.gt_installed()

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "Graphite CLI (gt) is not installed" in captured.err
        assert "npm install -g @withgraphite/graphite-cli" in captured.err


class TestEnsureGraphiteAvailable:
    """Tests for Ensure.graphite_available method."""

    def test_succeeds_when_graphite_enabled(self) -> None:
        """Ensure.graphite_available succeeds when graphite is a real implementation."""
        # Default context_for_test provides FakeGraphite (not GraphiteDisabled)
        ctx = context_for_test()

        # Should not raise
        Ensure.graphite_available(ctx)

    def test_exits_when_config_disabled(self) -> None:
        """Ensure.graphite_available raises SystemExit when disabled via config."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(SystemExit) as exc_info:
            Ensure.graphite_available(ctx)

        assert exc_info.value.code == 1

    def test_exits_when_not_installed(self) -> None:
        """Ensure.graphite_available raises SystemExit when gt not installed."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(SystemExit) as exc_info:
            Ensure.graphite_available(ctx)

        assert exc_info.value.code == 1

    def test_config_disabled_error_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Error message for CONFIG_DISABLED includes config enable instruction."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.CONFIG_DISABLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(SystemExit):
            Ensure.graphite_available(ctx)

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "requires Graphite to be enabled" in captured.err
        assert "erk config set use_graphite true" in captured.err

    def test_not_installed_error_message(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Error message for NOT_INSTALLED includes installation instructions."""
        disabled = GraphiteDisabled(reason=GraphiteDisabledReason.NOT_INSTALLED)
        ctx = context_for_test(graphite=disabled)

        with pytest.raises(SystemExit):
            Ensure.graphite_available(ctx)

        captured = capsys.readouterr()
        assert "Error:" in captured.err
        assert "requires Graphite to be installed" in captured.err
        assert "npm install -g @withgraphite/graphite-cli" in captured.err
