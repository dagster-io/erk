"""Tests for hook atomicity during installation and updates."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from erk.cli.commands.kit.install import _perform_atomic_hook_update
from erk.kits.hooks.installer import install_hooks
from erk.kits.hooks.models import HookDefinition
from erk.kits.hooks.settings import load_settings


def create_test_kit_with_hooks(kit_dir: Path, kit_id: str) -> Path:
    """Create a test kit with hook scripts."""
    kit_root = kit_dir / kit_id
    kit_root.mkdir(parents=True, exist_ok=True)

    # Create hook scripts
    hooks_dir = kit_root / "hooks"
    hooks_dir.mkdir(exist_ok=True)

    script1 = hooks_dir / "hook1.py"
    script1.write_text("print('Hook 1')")

    script2 = hooks_dir / "hook2.py"
    script2.write_text("print('Hook 2')")

    return kit_root


def test_atomic_hook_update_success():
    """Test successful atomic hook update."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        kit_dir = project_dir / "kit_source"
        kit_root = create_test_kit_with_hooks(kit_dir, "test-kit")

        # Create initial hooks
        old_hooks = [
            HookDefinition(
                id="old_hook",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit old_hook",
                description="Old hook",
            )
        ]

        # Install initial hooks
        install_hooks("test-kit", old_hooks, project_dir)

        # Verify initial hooks installed
        settings = load_settings(project_dir / ".claude" / "settings.json")
        assert settings.hooks is not None
        assert "PostToolUse" in settings.hooks
        initial_hooks = settings.hooks["PostToolUse"]
        assert len(initial_hooks) > 0

        # Create new hooks
        new_hooks = [
            HookDefinition(
                id="new_hook1",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit new_hook1",
                description="New hook 1",
            ),
            HookDefinition(
                id="new_hook2",
                lifecycle="UserPromptSubmit",
                matcher="*",
                invocation="dot-agent run test-kit new_hook2",
                description="New hook 2",
            ),
        ]

        # Perform atomic update - pass old_hooks so they get removed
        hooks_count = _perform_atomic_hook_update(
            kit_id="test-kit",
            manifest_hooks=new_hooks,
            kit_path=kit_root,
            project_dir=project_dir,
            old_hooks=old_hooks,
        )

        assert hooks_count == 2

        # Verify new hooks installed
        settings = load_settings(project_dir / ".claude" / "settings.json")
        assert settings.hooks is not None
        assert "PostToolUse" in settings.hooks
        assert "UserPromptSubmit" in settings.hooks

        # Verify old hooks removed
        all_hooks = []
        for lifecycle_groups in settings.hooks.values():
            for group in lifecycle_groups:
                all_hooks.extend(group.hooks)

        # Check that no old hook IDs remain
        for hook in all_hooks:
            assert "ERK_HOOK_ID=" in hook.command
            assert "ERK_HOOK_ID=old_hook" not in hook.command


def test_atomic_hook_update_rollback_on_failure():
    """Test that hooks are rolled back when installation fails."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        kit_dir = project_dir / "kit_source"
        kit_root = create_test_kit_with_hooks(kit_dir, "test-kit")

        # Create initial hooks
        old_hooks = [
            HookDefinition(
                id="existing_hook",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit existing_hook",
                description="Existing hook",
            )
        ]

        # Install initial hooks
        install_hooks("test-kit", old_hooks, project_dir)

        # Save initial state
        initial_settings = load_settings(project_dir / ".claude" / "settings.json")
        hooks_dir = project_dir / ".claude" / "hooks" / "test-kit"
        initial_hook_files = list(hooks_dir.glob("*")) if hooks_dir.exists() else []

        # Create new hooks
        new_hooks = [
            HookDefinition(
                id="new_hook1",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit new_hook1",
                description="New hook 1",
            ),
            HookDefinition(
                id="failing_hook",
                lifecycle="UserPromptSubmit",
                matcher="*",
                invocation="dot-agent run test-kit failing_hook",
                description="Failing hook",
            ),
        ]

        # Mock install_hooks to fail after removing old hooks
        with patch("erk.cli.commands.kit.install.install_hooks") as mock_install:
            mock_install.side_effect = RuntimeError("Hook script not found")

            # Attempt atomic update - should fail and rollback
            with pytest.raises(RuntimeError, match="Hook script not found"):
                _perform_atomic_hook_update(
                    kit_id="test-kit",
                    manifest_hooks=new_hooks,
                    kit_path=kit_root,
                    project_dir=project_dir,
                )

        # Verify hooks were restored to initial state
        restored_settings = load_settings(project_dir / ".claude" / "settings.json")
        assert restored_settings == initial_settings

        # Verify hook files were restored
        if hooks_dir.exists():
            restored_files = list(hooks_dir.glob("*"))
            assert len(restored_files) == len(initial_hook_files)


def test_atomic_hook_update_with_no_existing_hooks():
    """Test atomic update when no existing hooks are present."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        kit_dir = project_dir / "kit_source"
        kit_root = create_test_kit_with_hooks(kit_dir, "test-kit")

        # Create new hooks
        new_hooks = [
            HookDefinition(
                id="new_hook",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit new_hook",
                description="New hook",
            ),
        ]

        # Perform atomic update (no existing hooks to backup)
        hooks_count = _perform_atomic_hook_update(
            kit_id="test-kit",
            manifest_hooks=new_hooks,
            kit_path=kit_root,
            project_dir=project_dir,
        )

        assert hooks_count == 1

        # Verify hooks installed
        settings = load_settings(project_dir / ".claude" / "settings.json")
        assert settings.hooks is not None
        assert "PostToolUse" in settings.hooks


def test_atomic_hook_update_removes_hooks_when_none_in_manifest():
    """Test that atomic update removes hooks when manifest has none."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        kit_dir = project_dir / "kit_source"
        kit_root = create_test_kit_with_hooks(kit_dir, "test-kit")

        # Create initial hooks
        old_hooks = [
            HookDefinition(
                id="old_hook",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit old_hook",
                description="Old hook",
            )
        ]

        # Install initial hooks
        install_hooks("test-kit", old_hooks, project_dir)

        # Perform atomic update with no hooks - pass old_hooks so they get removed
        hooks_count = _perform_atomic_hook_update(
            kit_id="test-kit",
            manifest_hooks=None,  # No hooks in new manifest
            kit_path=kit_root,
            project_dir=project_dir,
            old_hooks=old_hooks,
        )

        assert hooks_count == 0

        # Verify hooks removed from settings
        settings = load_settings(project_dir / ".claude" / "settings.json")

        # Check no hooks from this kit remain
        all_hooks = []
        if settings.hooks:
            for lifecycle_groups in settings.hooks.values():
                for group in lifecycle_groups:
                    all_hooks.extend(group.hooks)

        for hook in all_hooks:
            assert "ERK_HOOK_ID=old_hook" not in hook.command


def test_atomic_hook_update_cleans_up_partial_installation_on_failure():
    """Test that partial hook installation is cleaned up on failure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        project_dir = Path(temp_dir)
        kit_dir = project_dir / "kit_source"
        kit_root = create_test_kit_with_hooks(kit_dir, "test-kit")

        # Create hooks that will fail during installation
        new_hooks = [
            HookDefinition(
                id="new_hook",
                lifecycle="PostToolUse",
                matcher="*",
                invocation="dot-agent run test-kit new_hook",
                description="New hook",
            ),
        ]

        # Mock install_hooks to fail
        with patch("erk.cli.commands.kit.install.install_hooks") as mock_install:
            mock_install.side_effect = RuntimeError("Installation failed midway")

            # Attempt atomic update - should fail and clean up
            with pytest.raises(RuntimeError, match="Installation failed midway"):
                _perform_atomic_hook_update(
                    kit_id="test-kit",
                    manifest_hooks=new_hooks,
                    kit_path=kit_root,
                    project_dir=project_dir,
                )

        # Verify settings were restored (no partial installation)
        settings_path = project_dir / ".claude" / "settings.json"
        if settings_path.exists():
            settings = load_settings(settings_path)
            # Should have no hooks from this kit
            if settings.hooks:
                for lifecycle_groups in settings.hooks.values():
                    for group in lifecycle_groups:
                        for hook in group.hooks:
                            assert "ERK_HOOK_ID=new_hook" not in hook.command
