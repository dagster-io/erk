"""Tests for install_kit operation with hooks."""

from pathlib import Path

import yaml

from erk.kits.hooks.settings import extract_kit_id_from_command, load_settings
from erk.kits.operations.install import install_kit
from erk.kits.sources.resolver import ResolvedKit


def test_install_kit_installs_hooks(tmp_path: Path) -> None:
    """Test that install_kit installs hooks from kit manifest to settings.json.

    This is a regression test for the bug where install_kit only installed
    artifacts but never called install_hooks, causing 'erk kit sync --force'
    to fail to update hook configuration in settings.json.
    """
    # Setup: Create a kit with hooks
    kit_dir = tmp_path / "test-kit"
    kit_dir.mkdir()

    # Create manifest with hook definition
    manifest_data = {
        "name": "test-kit",
        "version": "1.0.0",
        "description": "Test kit with hooks",
        "artifacts": {
            "agent": ["agents/test-agent.md"],
        },
        "hooks": [
            {
                "id": "test-hook",
                "lifecycle": "UserPromptSubmit",
                "matcher": "*",
                "invocation": "erk kit exec test-kit test-hook",
                "description": "Test hook",
                "timeout": 30,
            }
        ],
    }

    manifest_path = kit_dir / "kit.yaml"
    manifest_path.write_text(yaml.dump(manifest_data), encoding="utf-8")

    # Create artifact
    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("# Test Agent", encoding="utf-8")

    # Create hook script
    scripts_dir = kit_dir / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "test_hook.py").write_text(
        "#!/usr/bin/env python3\nprint('Test hook')", encoding="utf-8"
    )

    # Create project directory
    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Create ResolvedKit
    resolved = ResolvedKit(
        kit_id="test-kit",
        source_type="bundled",
        version="1.0.0",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Execute: Install the kit
    install_kit(resolved, project_dir, overwrite=False)

    # Verify: Check that hooks were installed to settings.json
    settings_path = project_dir / ".claude" / "settings.json"
    assert settings_path.exists(), "settings.json should be created"

    settings = load_settings(settings_path)
    assert settings.hooks is not None, "Hooks should be present in settings"
    assert "UserPromptSubmit" in settings.hooks, "UserPromptSubmit lifecycle should exist"

    # Find the hook in settings
    found_hook = False
    for matcher_group in settings.hooks["UserPromptSubmit"]:
        if matcher_group.matcher == "*":
            for hook_entry in matcher_group.hooks:
                kit_id = extract_kit_id_from_command(hook_entry.command)
                if kit_id == "test-kit":
                    # Verify hook ID is in command
                    assert "ERK_HOOK_ID=test-hook" in hook_entry.command
                    assert hook_entry.timeout == 30
                    found_hook = True
                    break

    assert found_hook, "Hook should be found in settings.json"


def test_install_kit_without_hooks_does_not_create_hook_entries(tmp_path: Path) -> None:
    """Test that install_kit handles kits without hooks gracefully."""
    # Setup: Create a kit without hooks
    kit_dir = tmp_path / "no-hooks-kit"
    kit_dir.mkdir()

    manifest_data = {
        "name": "no-hooks-kit",
        "version": "1.0.0",
        "description": "Test kit without hooks",
        "artifacts": {
            "agent": ["agents/test-agent.md"],
        },
    }

    manifest_path = kit_dir / "kit.yaml"
    manifest_path.write_text(yaml.dump(manifest_data), encoding="utf-8")

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "test-agent.md").write_text("# Test Agent", encoding="utf-8")

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    resolved = ResolvedKit(
        kit_id="no-hooks-kit",
        source_type="bundled",
        version="1.0.0",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    # Execute: Install the kit
    install_kit(resolved, project_dir, overwrite=False)

    # Verify: No hooks should be in settings.json
    settings_path = project_dir / ".claude" / "settings.json"

    # Settings.json might not exist if no hooks were installed
    if settings_path.exists():
        settings = load_settings(settings_path)
        if settings.hooks is not None:
            # If hooks exist, verify no hooks for this kit
            for lifecycle_hooks in settings.hooks.values():
                for matcher_group in lifecycle_hooks:
                    for hook_entry in matcher_group.hooks:
                        kit_id = extract_kit_id_from_command(hook_entry.command)
                        assert kit_id != "no-hooks-kit", "No hooks should exist for this kit"


def test_install_kit_replaces_old_hooks_on_reinstall(tmp_path: Path) -> None:
    """Test that reinstalling a kit with different hooks replaces old configuration."""
    kit_dir = tmp_path / "versioned-kit"
    kit_dir.mkdir()

    project_dir = tmp_path / "project"
    project_dir.mkdir()

    # Install v1 with one hook
    manifest_v1 = {
        "name": "versioned-kit",
        "version": "1.0.0",
        "description": "Version 1",
        "artifacts": {"agent": ["agents/v1-agent.md"]},
        "hooks": [
            {
                "id": "old-hook",
                "lifecycle": "UserPromptSubmit",
                "matcher": "*",
                "invocation": "erk kit exec versioned-kit old-hook",
                "description": "Old hook",
                "timeout": 30,
            }
        ],
    }

    manifest_path = kit_dir / "kit.yaml"
    manifest_path.write_text(yaml.dump(manifest_v1), encoding="utf-8")

    agents_dir = kit_dir / "agents"
    agents_dir.mkdir(exist_ok=True)
    (agents_dir / "v1-agent.md").write_text("# V1", encoding="utf-8")

    scripts_dir = kit_dir / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    (scripts_dir / "old.py").write_text("print('old')", encoding="utf-8")

    resolved_v1 = ResolvedKit(
        kit_id="versioned-kit",
        source_type="bundled",
        version="1.0.0",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    install_kit(resolved_v1, project_dir, overwrite=False)

    # Install v2 with different hook
    manifest_v2 = {
        "name": "versioned-kit",
        "version": "2.0.0",
        "description": "Version 2",
        "artifacts": {"agent": ["agents/v2-agent.md"]},
        "hooks": [
            {
                "id": "new-hook",
                "lifecycle": "UserPromptSubmit",
                "matcher": "*",
                "invocation": "erk kit exec versioned-kit new-hook",
                "description": "New hook",
                "timeout": 60,
            }
        ],
    }

    manifest_path.write_text(yaml.dump(manifest_v2), encoding="utf-8")
    (agents_dir / "v2-agent.md").write_text("# V2", encoding="utf-8")
    (scripts_dir / "new.py").write_text("print('new')", encoding="utf-8")

    resolved_v2 = ResolvedKit(
        kit_id="versioned-kit",
        source_type="bundled",
        version="2.0.0",
        manifest_path=manifest_path,
        artifacts_base=kit_dir,
    )

    install_kit(resolved_v2, project_dir, overwrite=True)

    # Verify: Only new hook exists
    settings_path = project_dir / ".claude" / "settings.json"
    settings = load_settings(settings_path)

    hook_ids = []
    if settings.hooks and "UserPromptSubmit" in settings.hooks:
        for matcher_group in settings.hooks["UserPromptSubmit"]:
            for hook_entry in matcher_group.hooks:
                kit_id = extract_kit_id_from_command(hook_entry.command)
                if kit_id == "versioned-kit":
                    # Extract hook ID
                    import re

                    match = re.search(r"ERK_HOOK_ID=(\S+)", hook_entry.command)
                    if match:
                        hook_ids.append(match.group(1))

    assert "old-hook" not in hook_ids, "Old hook should be removed"
    assert "new-hook" in hook_ids, "New hook should be present"
    assert len(hook_ids) == 1, "Should only have one hook"
