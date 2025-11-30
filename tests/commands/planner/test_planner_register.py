"""Tests for planner register command."""

from datetime import UTC, datetime
from unittest.mock import patch

from click.testing import CliRunner
from erk_shared.integrations.time.fake import FakeTime

from erk.cli.cli import cli
from erk.core.context import ErkContext
from erk.core.planner.registry_fake import FakePlannerRegistry
from erk.core.planner.types import RegisteredPlanner


def _make_planner(
    name: str = "test-planner",
    gh_name: str = "test-gh-name",
    repository: str = "test-owner/test-repo",
    configured: bool = False,
) -> RegisteredPlanner:
    """Helper to create test planners."""
    return RegisteredPlanner(
        name=name,
        gh_name=gh_name,
        repository=repository,
        configured=configured,
        registered_at=datetime(2025, 1, 1, 12, 0, 0, tzinfo=UTC),
        last_connected_at=None,
    )


def test_register_duplicate_name_shows_error() -> None:
    """Test register with existing name shows error."""
    existing = _make_planner(name="my-planner")
    registry = FakePlannerRegistry(planners=[existing])
    ctx = ErkContext.for_test(planner_registry=registry)

    runner = CliRunner()
    result = runner.invoke(cli, ["planner", "register", "my-planner"], obj=ctx)

    assert result.exit_code == 1
    assert "already exists" in result.output


def test_register_no_codespaces_shows_error() -> None:
    """Test register with no available codespaces shows error."""
    registry = FakePlannerRegistry()
    ctx = ErkContext.for_test(planner_registry=registry)

    runner = CliRunner()

    # Mock subprocess to return empty list
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "[]"
        result = runner.invoke(cli, ["planner", "register", "my-planner"], obj=ctx)

    assert result.exit_code == 1
    assert "No codespaces found" in result.output


def test_register_codespace_selection() -> None:
    """Test registering a codespace from list."""
    registry = FakePlannerRegistry()
    fake_time = FakeTime(current_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC))
    ctx = ErkContext.for_test(planner_registry=registry, time=fake_time)

    runner = CliRunner()

    # Mock subprocess to return codespace list
    codespaces_json = """[
        {"name": "cs-abc123", "repository": "owner/repo1", "displayName": "My Codespace 1"},
        {"name": "cs-def456", "repository": "owner/repo2", "displayName": "My Codespace 2"}
    ]"""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = codespaces_json

        # Select the first codespace
        result = runner.invoke(cli, ["planner", "register", "my-planner"], input="1\n", obj=ctx)

    assert result.exit_code == 0
    assert "Registered planner 'my-planner'" in result.output

    # Verify planner was registered
    registered = registry.get("my-planner")
    assert registered is not None
    assert registered.name == "my-planner"
    assert registered.gh_name == "cs-abc123"
    assert registered.repository == "owner/repo1"
    assert registered.configured is False


def test_register_first_planner_sets_default() -> None:
    """Test that first registered planner is set as default."""
    registry = FakePlannerRegistry()
    fake_time = FakeTime(current_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC))
    ctx = ErkContext.for_test(planner_registry=registry, time=fake_time)

    runner = CliRunner()

    codespaces_json = """[{"name": "cs-abc", "repository": "owner/repo", "displayName": "CS"}]"""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = codespaces_json

        result = runner.invoke(cli, ["planner", "register", "first-planner"], input="1\n", obj=ctx)

    assert result.exit_code == 0
    assert "set as default" in result.output

    # Verify it was set as default
    assert registry.get_default_name() == "first-planner"


def test_register_subsequent_planner_not_default() -> None:
    """Test that subsequent planners are not automatically set as default."""
    existing = _make_planner(name="existing")
    registry = FakePlannerRegistry(planners=[existing], default_planner="existing")
    fake_time = FakeTime(current_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC))
    ctx = ErkContext.for_test(planner_registry=registry, time=fake_time)

    runner = CliRunner()

    codespaces_json = """[{"name": "cs-abc", "repository": "owner/repo", "displayName": "CS"}]"""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = codespaces_json

        result = runner.invoke(cli, ["planner", "register", "second-planner"], input="1\n", obj=ctx)

    assert result.exit_code == 0
    assert "set as default" not in result.output

    # Default should still be the original
    assert registry.get_default_name() == "existing"


def test_register_prompts_for_configure() -> None:
    """Test that register prompts to run configure."""
    registry = FakePlannerRegistry()
    fake_time = FakeTime(current_time=datetime(2025, 6, 15, 10, 0, 0, tzinfo=UTC))
    ctx = ErkContext.for_test(planner_registry=registry, time=fake_time)

    runner = CliRunner()

    codespaces_json = """[{"name": "cs-abc", "repository": "owner/repo", "displayName": "CS"}]"""

    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = codespaces_json

        result = runner.invoke(cli, ["planner", "register", "my-planner"], input="1\n", obj=ctx)

    assert result.exit_code == 0
    assert "erk planner configure my-planner" in result.output
