"""CLI tests for hooks integration in install/remove commands."""

import os
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from erk.cli.commands.kit.install import install
from erk.cli.commands.kit.remove import remove
from erk.kits.hooks.settings import extract_kit_id_from_command, load_settings
from erk.kits.io.state import load_project_config
from erk.kits.sources.resolver import KitResolver
from tests.fakes.fake_local_source import FakeLocalSource


def create_kit_with_hooks(
    kit_dir: Path,
    kit_id: str,
    version: str = "1.0.0",
    hooks: list[dict] | None = None,
) -> Path:
    """Create a mock kit directory with manifest and optional hooks.

    Args:
        kit_dir: Directory to create kit in
        kit_id: Kit identifier
        version: Kit version
        hooks: List of hook definitions (each dict should have id, lifecycle, matcher,
            invocation, description)

    Returns:
        Path to the created kit directory
    """
    kit_root = kit_dir / kit_id
    kit_root.mkdir(parents=True, exist_ok=True)

    # Use kit_id in artifact name to avoid conflicts when installing multiple kits
    artifact_name = f"{kit_id}-agent.md"

    # Create manifest
    manifest_data = {
        "name": kit_id,
        "version": version,
        "description": f"Test kit {kit_id}",
        "artifacts": {
            "agent": [f"agents/{artifact_name}"],
        },
    }

    if hooks:
        manifest_data["hooks"] = hooks

    manifest_path = kit_root / "kit.yaml"
    manifest_path.write_text(yaml.dump(manifest_data), encoding="utf-8")

    # Create artifact
    agents_dir = kit_root / "agents"
    agents_dir.mkdir(parents=True, exist_ok=True)
    (agents_dir / artifact_name).write_text(f"# Test Agent for {kit_id}", encoding="utf-8")

    return kit_root


def create_simple_hook(
    hook_id: str = "test-hook",
    lifecycle: str = "PreToolUse",
    matcher: str = "Bash:*",
    description: str = "Test hook",
    timeout: int = 30,
    kit_id: str = "test-kit",
) -> dict:
    """Create a simple hook definition dict."""
    return {
        "id": hook_id,
        "lifecycle": lifecycle,
        "matcher": matcher,
        "invocation": f"dot-agent run {kit_id} {hook_id}",
        "description": description,
        "timeout": timeout,
    }


def invoke_in_project(
    cli_runner: CliRunner,
    project_dir: Path,
    command,
    args: list[str],
):
    """Invoke a CLI command in a specific project directory with patched resolver.

    Note: This does NOT patch user directory - hooks should never touch user settings.
    """
    original_cwd = os.getcwd()
    try:
        os.chdir(project_dir)

        # Patch KitResolver to use FakeLocalSource for tests
        def patched_resolver_init(self, sources=None):
            if sources is None:
                sources = []
            # Always prepend FakeLocalSource for testing
            self.sources = [FakeLocalSource()] + sources

        with patch.object(KitResolver, "__init__", patched_resolver_init):
            return cli_runner.invoke(command, args, catch_exceptions=False)
    finally:
        os.chdir(original_cwd)


def assert_hook_installed(
    project_root: Path,
    kit_id: str,
    hook_id: str,
    expected_lifecycle: str,
    expected_matcher: str,
) -> None:
    """Assert that a hook is properly installed."""
    # Check settings.json has the hook
    settings_path = project_root / ".claude" / "settings.json"
    settings = load_settings(settings_path)
    assert settings.hooks is not None, "No hooks in settings.json"
    assert expected_lifecycle in settings.hooks, f"Lifecycle {expected_lifecycle} not in settings"

    # Find the hook in settings
    found = False
    for matcher_group in settings.hooks[expected_lifecycle]:
        if matcher_group.matcher == expected_matcher:
            for hook_entry in matcher_group.hooks:
                entry_kit_id = extract_kit_id_from_command(hook_entry.command)
                if entry_kit_id == kit_id:
                    import re

                    hook_id_match = re.search(r"ERK_HOOK_ID=(\S+)", hook_entry.command)
                    entry_hook_id = hook_id_match.group(1) if hook_id_match else None
                    if entry_hook_id == hook_id:
                        found = True
                        break
        if found:
            break

    assert found, f"Hook {kit_id}:{hook_id} not found in settings.json"


def assert_hook_not_installed(project_root: Path, kit_id: str) -> None:
    """Assert that no hooks are installed for a kit."""
    # Check settings.json has no hooks for this kit
    settings_path = project_root / ".claude" / "settings.json"
    if settings_path.exists():
        settings = load_settings(settings_path)
        if settings.hooks:
            for lifecycle_hooks in settings.hooks.values():
                for matcher_group in lifecycle_hooks:
                    for hook_entry in matcher_group.hooks:
                        entry_kit_id = extract_kit_id_from_command(hook_entry.command)
                        assert entry_kit_id != kit_id, f"Found hook for {kit_id} in settings"


class TestInstallCommandWithHooks:
    """Tests for install command hooks integration."""

    def test_install_kit_with_single_hook(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test installing a kit with a single hook definition."""
        # Setup
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        hook = create_simple_hook(
            hook_id="my-hook",
            lifecycle="PreToolUse",
            matcher="Bash:git*",
            description="Check before git",
            kit_id="test-kit",
        )

        kit_root = create_kit_with_hooks(kits_dir, "test-kit", hooks=[hook])

        # Install
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Verify success
        assert result.exit_code == 0, f"Install failed: {result.output}"
        assert "✓ Installed" in result.output
        assert "v1.0.0" in result.output
        assert "Installed 1 hook(s)" in result.output

        # Verify hook installed
        assert_hook_installed(
            project_dir,
            "test-kit",
            "my-hook",
            "PreToolUse",
            "Bash:git*",
        )

        # Verify config includes hooks
        config = load_project_config(project_dir)
        assert config is not None, "Config not found"
        assert "test-kit" in config.kits
        installed_kit = config.kits["test-kit"]
        assert len(installed_kit.hooks) == 1
        assert installed_kit.hooks[0].id == "my-hook"

    def test_install_kit_with_multiple_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test installing a kit with multiple hooks."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        hooks = [
            create_simple_hook(
                hook_id="pre-hook",
                lifecycle="PreToolUse",
                matcher="Bash:git*",
                kit_id="multi-kit",
            ),
            create_simple_hook(
                hook_id="post-hook",
                lifecycle="PostToolUse",
                matcher="Bash:*",
                kit_id="multi-kit",
            ),
            create_simple_hook(
                hook_id="pre-hook-2",
                lifecycle="PreToolUse",
                matcher="Edit:*",
                kit_id="multi-kit",
            ),
        ]

        kit_root = create_kit_with_hooks(kits_dir, "multi-kit", hooks=hooks)

        # Install
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Verify
        assert result.exit_code == 0
        assert "Installed 3 hook(s)" in result.output

        # Verify all hooks installed
        assert_hook_installed(project_dir, "multi-kit", "pre-hook", "PreToolUse", "Bash:git*")
        assert_hook_installed(project_dir, "multi-kit", "post-hook", "PostToolUse", "Bash:*")
        assert_hook_installed(project_dir, "multi-kit", "pre-hook-2", "PreToolUse", "Edit:*")

    def test_install_kit_without_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test installing a kit that has no hooks field."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Create kit without hooks
        kit_root = create_kit_with_hooks(kits_dir, "no-hooks-kit", hooks=None)

        # Install
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Verify
        assert result.exit_code == 0
        assert "✓ Installed" in result.output
        # Should NOT have hooks message
        assert "hook(s)" not in result.output.lower()

        # Verify no hooks installed
        assert_hook_not_installed(project_dir, "no-hooks-kit")

    def test_install_hooks_project_only(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that hooks are only installed for project target.

        Note: Hooks are NEVER installed to user directory, only project.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        hook = create_simple_hook(hook_id="proj-hook", kit_id="project-only-kit")
        kit_root = create_kit_with_hooks(kits_dir, "project-only-kit", hooks=[hook])

        # Install kit (hooks should be installed)
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Should have hooks installed
        assert result.exit_code == 0
        assert "✓ Installed" in result.output
        assert "Installed 1 hook(s)" in result.output
        assert_hook_installed(project_dir, "project-only-kit", "proj-hook", "PreToolUse", "Bash:*")

    def test_install_kit_with_empty_hooks_list(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test installing a kit with empty hooks list."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Create kit with empty hooks list
        kit_root = create_kit_with_hooks(kits_dir, "empty-hooks-kit", hooks=[])

        # Install
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Verify
        assert result.exit_code == 0
        assert "✓ Installed" in result.output
        # Should not have hooks message
        assert "hook(s)" not in result.output.lower()

        assert_hook_not_installed(project_dir, "empty-hooks-kit")

    def test_install_hooks_replaces_previous_installation(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that reinstalling a kit replaces old hooks with new ones."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install v1 with 2 hooks
        hooks_v1 = [
            create_simple_hook(hook_id="hook-1", kit_id="versioned-kit"),
            create_simple_hook(hook_id="hook-2", kit_id="versioned-kit"),
        ]
        kit_root_v1 = create_kit_with_hooks(
            kits_dir, "versioned-kit", version="1.0.0", hooks=hooks_v1
        )

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root_v1)],
        )
        assert result.exit_code == 0
        assert "Installed 2 hook(s)" in result.output

        # Install v2 with 3 different hooks
        hooks_v2 = [
            create_simple_hook(hook_id="hook-3", kit_id="versioned-kit"),
            create_simple_hook(hook_id="hook-4", kit_id="versioned-kit"),
            create_simple_hook(hook_id="hook-5", kit_id="versioned-kit"),
        ]
        kit_root_v2 = create_kit_with_hooks(
            kits_dir, "versioned-kit", version="2.0.0", hooks=hooks_v2
        )

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root_v2), "--force"],
        )
        assert result.exit_code == 0
        assert "Installed 3 hook(s)" in result.output

        # Verify new hooks exist
        assert_hook_installed(project_dir, "versioned-kit", "hook-3", "PreToolUse", "Bash:*")
        assert_hook_installed(project_dir, "versioned-kit", "hook-4", "PreToolUse", "Bash:*")
        assert_hook_installed(project_dir, "versioned-kit", "hook-5", "PreToolUse", "Bash:*")

        # Verify old hooks don't exist in settings
        settings_path = project_dir / ".claude" / "settings.json"
        settings = load_settings(settings_path)
        all_hook_ids = []
        if settings.hooks:
            for lifecycle_hooks in settings.hooks.values():
                for matcher_group in lifecycle_hooks:
                    for hook_entry in matcher_group.hooks:
                        entry_kit_id = extract_kit_id_from_command(hook_entry.command)
                        if entry_kit_id == "versioned-kit":
                            import re

                            pattern = r"ERK_HOOK_ID=(\S+)"
                            hook_id_match = re.search(pattern, hook_entry.command)
                            if hook_id_match:
                                all_hook_ids.append(hook_id_match.group(1))

        assert "hook-1" not in all_hook_ids
        assert "hook-2" not in all_hook_ids
        assert "hook-3" in all_hook_ids
        assert "hook-4" in all_hook_ids
        assert "hook-5" in all_hook_ids

    def test_install_hooks_with_nested_script_paths(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test that nested script paths are flattened correctly."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        hook = create_simple_hook(
            hook_id="nested-hook",
            kit_id="nested-kit",
        )

        kit_root = create_kit_with_hooks(kits_dir, "nested-kit", hooks=[hook])

        # Install
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Verify
        assert result.exit_code == 0
        assert "Installed 1 hook(s)" in result.output

        # Verify hook installed in settings (no script files are copied anymore)
        assert_hook_installed(project_dir, "nested-kit", "nested-hook", "PreToolUse", "Bash:*")

    def test_install_hook_with_missing_script(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that all hooks are installed (no script validation anymore)."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Create hooks
        hooks = [
            create_simple_hook(hook_id="good-hook", kit_id="partial-kit"),
            create_simple_hook(hook_id="bad-hook", kit_id="partial-kit"),
            create_simple_hook(hook_id="good-hook-2", kit_id="partial-kit"),
        ]

        kit_root = create_kit_with_hooks(kits_dir, "partial-kit", hooks=hooks)

        # Install
        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )

        # Should succeed
        assert result.exit_code == 0
        # Should install all 3 hooks (no script validation)
        assert "Installed 3 hook(s)" in result.output

        # Verify all hooks installed
        assert_hook_installed(project_dir, "partial-kit", "good-hook", "PreToolUse", "Bash:*")
        assert_hook_installed(project_dir, "partial-kit", "bad-hook", "PreToolUse", "Bash:*")
        assert_hook_installed(project_dir, "partial-kit", "good-hook-2", "PreToolUse", "Bash:*")

    def test_install_preserves_other_kit_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that installing a kit preserves hooks from other kits."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install kit-a
        hook_a = create_simple_hook(hook_id="hook-a", kit_id="kit-a")
        kit_a_root = create_kit_with_hooks(kits_dir, "kit-a", hooks=[hook_a])

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_a_root)],
        )
        assert result.exit_code == 0, f"kit-a install failed: {result.output}"

        # Install kit-b (with unique artifact names to avoid conflicts)
        hook_b = create_simple_hook(hook_id="hook-b", kit_id="kit-b")

        # Create kit-b with different artifact name
        kit_b_dir = kits_dir / "kit-b"
        kit_b_dir.mkdir(parents=True, exist_ok=True)

        manifest_data = {
            "name": "kit-b",
            "version": "1.0.0",
            "description": "Test kit kit-b",
            "artifacts": {"agent": ["agents/kit-b-agent.md"]},
            "hooks": [
                {
                    "id": hook_b["id"],
                    "lifecycle": hook_b["lifecycle"],
                    "matcher": hook_b["matcher"],
                    "invocation": hook_b["invocation"],
                    "description": hook_b["description"],
                    "timeout": hook_b["timeout"],
                }
            ],
        }

        (kit_b_dir / "kit.yaml").write_text(yaml.dump(manifest_data), encoding="utf-8")
        agents_dir = kit_b_dir / "agents"
        agents_dir.mkdir(parents=True, exist_ok=True)
        (agents_dir / "kit-b-agent.md").write_text("# Kit B Agent", encoding="utf-8")

        scripts_dir = kit_b_dir / "scripts"
        scripts_dir.mkdir(parents=True, exist_ok=True)
        (scripts_dir / "b.py").write_text(
            "#!/usr/bin/env python3\nprint('Hook b')", encoding="utf-8"
        )

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_b_dir)],
        )
        assert result.exit_code == 0, f"kit-b install failed: {result.output}"

        # Verify both hooks exist
        assert_hook_installed(project_dir, "kit-a", "hook-a", "PreToolUse", "Bash:*")
        assert_hook_installed(project_dir, "kit-b", "hook-b", "PreToolUse", "Bash:*")


class TestRemoveCommandWithHooks:
    """Tests for remove command hooks integration."""

    def test_remove_kit_with_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test removing a kit that has hooks installed."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install kit with hooks
        hook = create_simple_hook(hook_id="remove-me", kit_id="remove-kit")
        kit_root = create_kit_with_hooks(kits_dir, "remove-kit", hooks=[hook])

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )
        assert result.exit_code == 0

        # Verify hook installed
        assert_hook_installed(project_dir, "remove-kit", "remove-me", "PreToolUse", "Bash:*")

        # Remove kit
        result = invoke_in_project(
            cli_runner,
            project_dir,
            remove,
            ["remove-kit"],
        )

        # Verify success
        assert result.exit_code == 0
        assert "✓ Removed" in result.output
        assert "Removed 1 hook(s)" in result.output

        # Verify hook removed
        assert_hook_not_installed(project_dir, "remove-kit")

    def test_remove_kit_without_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test removing a kit that has no hooks."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install kit without hooks
        kit_root = create_kit_with_hooks(kits_dir, "no-hooks-remove-kit", hooks=None)

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )
        assert result.exit_code == 0

        # Remove kit
        result = invoke_in_project(
            cli_runner,
            project_dir,
            remove,
            ["no-hooks-remove-kit"],
        )

        # Verify
        assert result.exit_code == 0
        assert "✓ Removed" in result.output
        # Should NOT have hooks message
        assert "hook(s)" not in result.output.lower()

    def test_remove_hooks_project_only(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that hooks removal only happens at project level.

        Note: Hooks are NEVER installed/removed from user directory, only project.
        """
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install to project with hooks
        hook = create_simple_hook(hook_id="proj-hook", kit_id="proj-kit")
        kit_root = create_kit_with_hooks(kits_dir, "proj-kit", hooks=[hook])

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )
        assert result.exit_code == 0
        assert "Installed 1 hook(s)" in result.output

        # Remove from project
        result = invoke_in_project(
            cli_runner,
            project_dir,
            remove,
            ["proj-kit"],
        )

        # Should succeed with hooks message
        assert result.exit_code == 0
        assert "Removed 1 hook(s)" in result.output

    def test_remove_preserves_other_kit_hooks(self, cli_runner: CliRunner, tmp_path: Path) -> None:
        """Test that removing one kit preserves hooks from other kits."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install two kits with hooks
        hook_a = create_simple_hook(hook_id="keep-hook", kit_id="keep-kit")
        kit_a_root = create_kit_with_hooks(kits_dir, "keep-kit", hooks=[hook_a])

        hook_b = create_simple_hook(hook_id="remove-hook", kit_id="remove-kit")
        kit_b_root = create_kit_with_hooks(kits_dir, "remove-kit", hooks=[hook_b])

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_a_root)],
        )
        assert result.exit_code == 0

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_b_root)],
        )
        assert result.exit_code == 0

        # Verify both installed
        assert_hook_installed(project_dir, "keep-kit", "keep-hook", "PreToolUse", "Bash:*")
        assert_hook_installed(project_dir, "remove-kit", "remove-hook", "PreToolUse", "Bash:*")

        # Remove kit-b
        result = invoke_in_project(
            cli_runner,
            project_dir,
            remove,
            ["remove-kit"],
        )
        assert result.exit_code == 0
        assert "Removed 1 hook(s)" in result.output

        # Verify keep-kit hook still exists
        assert_hook_installed(project_dir, "keep-kit", "keep-hook", "PreToolUse", "Bash:*")

        # Verify remove-kit hook is gone
        assert_hook_not_installed(project_dir, "remove-kit")

    def test_remove_kit_hooks_already_manually_removed(
        self, cli_runner: CliRunner, tmp_path: Path
    ) -> None:
        """Test graceful handling when hook directory was manually deleted."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        kits_dir = tmp_path / "kits"
        kits_dir.mkdir()

        # Install kit with hooks
        hook = create_simple_hook(hook_id="manual-remove", kit_id="manual-kit")
        kit_root = create_kit_with_hooks(kits_dir, "manual-kit", hooks=[hook])

        result = invoke_in_project(
            cli_runner,
            project_dir,
            install,
            [str(kit_root)],
        )
        assert result.exit_code == 0

        # Remove kit (should work normally)
        result = invoke_in_project(
            cli_runner,
            project_dir,
            remove,
            ["manual-kit"],
        )

        # Should succeed without error
        assert result.exit_code == 0
        assert "✓ Removed" in result.output
        # Should report hook removal from settings
        assert "Removed 1 hook(s)" in result.output
