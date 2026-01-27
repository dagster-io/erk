"""Unit tests for codespace set-default command."""

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.context import context_for_test
from erk_shared.gateway.codespace_registry.abc import RegisteredCodespace
from erk_shared.gateway.codespace_registry.fake import FakeCodespaceRegistry
from erk_shared.gateway.codespace_registry.real import RealCodespaceRegistry
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation


def test_set_default_shows_error_when_not_found() -> None:
    """set-default command shows error when codespace doesn't exist."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(
        cli, ["codespace", "set-default", "nonexistent"], obj=ctx, catch_exceptions=False
    )

    assert result.exit_code == 1
    assert "No codespace named 'nonexistent' found" in result.output
    assert "erk codespace list" in result.output


def test_set_default_updates_default(tmp_path: Path) -> None:
    """set-default command updates the default codespace."""
    runner = CliRunner()

    # Create a real registry with a codespace for this test
    config_path = tmp_path / "codespaces.toml"

    # Write initial config with a codespace
    config_path.write_text(
        """
schema_version = 1

[codespaces.mybox]
gh_name = "user-mybox-abc"
created_at = "2026-01-20T08:00:00"
""",
        encoding="utf-8",
    )

    # Create real registry for reading, fake for context injection
    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])

    fake_erk_installation = FakeErkInstallation(root_path=tmp_path)
    ctx = context_for_test(
        codespace_registry=codespace_registry, erk_installation=fake_erk_installation
    )

    result = runner.invoke(
        cli, ["codespace", "set-default", "mybox"], obj=ctx, catch_exceptions=False
    )

    assert result.exit_code == 0
    assert "Set 'mybox' as the default codespace" in result.output

    # Verify the file was updated
    real_registry = RealCodespaceRegistry.from_config_path(config_path)
    assert real_registry.get_default_name() == "mybox"


def test_set_default_confirms_success_message() -> None:
    """set-default command shows confirmation message on success."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])

    # Use tmp_path in the isolated filesystem
    with runner.isolated_filesystem() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write initial config
        config_path = tmp_path / "codespaces.toml"
        config_path.write_text(
            """
schema_version = 1

[codespaces.mybox]
gh_name = "user-mybox-abc"
created_at = "2026-01-20T08:00:00"
""",
            encoding="utf-8",
        )

        fake_erk_installation = FakeErkInstallation(root_path=tmp_path)
        ctx = context_for_test(
            codespace_registry=codespace_registry, erk_installation=fake_erk_installation
        )

        result = runner.invoke(
            cli, ["codespace", "set-default", "mybox"], obj=ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Set 'mybox' as the default codespace" in result.output
