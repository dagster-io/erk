"""Unit tests for codespace remove command."""

from datetime import datetime
from pathlib import Path

from click.testing import CliRunner

from erk.cli.cli import cli
from erk.core.codespace.registry_fake import FakeCodespaceRegistry
from erk.core.codespace.registry_real import RealCodespaceRegistry
from erk.core.codespace.types import RegisteredCodespace
from erk.core.context import context_for_test
from erk_shared.gateway.erk_installation.fake import FakeErkInstallation


def test_remove_shows_error_when_not_found() -> None:
    """remove command shows error when codespace doesn't exist."""
    runner = CliRunner()

    codespace_registry = FakeCodespaceRegistry()
    ctx = context_for_test(codespace_registry=codespace_registry)

    result = runner.invoke(
        cli, ["codespace", "remove", "nonexistent"], obj=ctx, catch_exceptions=False
    )

    assert result.exit_code == 1
    assert "No codespace named 'nonexistent' found" in result.output
    assert "erk codespace list" in result.output


def test_remove_requires_confirmation() -> None:
    """remove command prompts for confirmation before removing."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])

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

        # Input 'n' to decline confirmation
        result = runner.invoke(
            cli, ["codespace", "remove", "mybox"], obj=ctx, input="n\n", catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Cancelled" in result.output

        # Verify the codespace was NOT removed
        real_registry = RealCodespaceRegistry.from_config_path(config_path)
        assert real_registry.get("mybox") is not None


def test_remove_with_force_skips_confirmation() -> None:
    """remove --force skips confirmation and removes immediately."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs])

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
            cli, ["codespace", "remove", "--force", "mybox"], obj=ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Removed codespace 'mybox'" in result.output

        # Verify the codespace was removed
        real_registry = RealCodespaceRegistry.from_config_path(config_path)
        assert real_registry.get("mybox") is None


def test_remove_notes_when_clearing_default() -> None:
    """remove command notes when removing the default codespace."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")

    with runner.isolated_filesystem() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write initial config with default
        config_path = tmp_path / "codespaces.toml"
        config_path.write_text(
            """
schema_version = 1
default_codespace = "mybox"

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
            cli, ["codespace", "remove", "--force", "mybox"], obj=ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Removed codespace 'mybox'" in result.output
        assert "Default codespace has been cleared" in result.output


def test_remove_suggests_set_default_when_others_remain() -> None:
    """remove command suggests set-default when other codespaces exist."""
    runner = CliRunner()

    cs1 = RegisteredCodespace(
        name="box1", gh_name="user-box1-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    cs2 = RegisteredCodespace(
        name="box2", gh_name="user-box2-def", created_at=datetime(2026, 1, 20, 9, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs1, cs2], default_codespace="box1")

    with runner.isolated_filesystem() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write initial config with multiple codespaces
        config_path = tmp_path / "codespaces.toml"
        config_path.write_text(
            """
schema_version = 1
default_codespace = "box1"

[codespaces.box1]
gh_name = "user-box1-abc"
created_at = "2026-01-20T08:00:00"

[codespaces.box2]
gh_name = "user-box2-def"
created_at = "2026-01-20T09:00:00"
""",
            encoding="utf-8",
        )

        fake_erk_installation = FakeErkInstallation(root_path=tmp_path)
        ctx = context_for_test(
            codespace_registry=codespace_registry, erk_installation=fake_erk_installation
        )

        result = runner.invoke(
            cli, ["codespace", "remove", "--force", "box1"], obj=ctx, catch_exceptions=False
        )

        assert result.exit_code == 0
        assert "Removed codespace 'box1'" in result.output
        assert "Default codespace has been cleared" in result.output
        assert "erk codespace set-default" in result.output

        # Verify box1 was removed but box2 remains
        real_registry = RealCodespaceRegistry.from_config_path(config_path)
        assert real_registry.get("box1") is None
        assert real_registry.get("box2") is not None


def test_remove_mentions_default_in_confirmation() -> None:
    """remove command mentions 'currently the default' in confirmation prompt."""
    runner = CliRunner()

    cs = RegisteredCodespace(
        name="mybox", gh_name="user-mybox-abc", created_at=datetime(2026, 1, 20, 8, 0, 0)
    )
    codespace_registry = FakeCodespaceRegistry(codespaces=[cs], default_codespace="mybox")

    with runner.isolated_filesystem() as tmp_dir:
        tmp_path = Path(tmp_dir)

        # Write initial config
        config_path = tmp_path / "codespaces.toml"
        config_path.write_text(
            """
schema_version = 1
default_codespace = "mybox"

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

        # Input 'n' to see the prompt
        result = runner.invoke(
            cli, ["codespace", "remove", "mybox"], obj=ctx, input="n\n", catch_exceptions=False
        )

        assert "(currently the default)" in result.output
