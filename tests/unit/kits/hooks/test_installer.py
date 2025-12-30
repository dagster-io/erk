"""Tests for hook installation and removal operations."""

from pathlib import Path

from erk.kits.hooks.installer import install_hooks, remove_hooks
from erk.kits.hooks.models import HookDefinition
from erk.kits.hooks.settings import load_settings


def test_install_hooks_basic(tmp_project: Path) -> None:
    """Test installing a single hook to a project."""
    # Define hook
    hook_def = HookDefinition(
        id="test-hook",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit test-hook",
        description="Test hook",
        timeout=30,
    )

    # Install hooks
    count = install_hooks(
        kit_id="test-kit",
        hooks=[hook_def],
        project_root=tmp_project,
    )

    # Verify installation
    assert count == 1

    # Check settings.json updated
    settings_path = tmp_project / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = load_settings(settings_path)
    assert settings.hooks is not None
    assert "UserPromptSubmit" in settings.hooks

    lifecycle_hooks = settings.hooks["UserPromptSubmit"]
    assert len(lifecycle_hooks) == 1
    assert lifecycle_hooks[0].matcher == "**"
    assert len(lifecycle_hooks[0].hooks) == 1

    hook_entry = lifecycle_hooks[0].hooks[0]
    expected_cmd = "ERK_HOOK_ID=test-hook erk kit exec test-kit test-hook"
    assert hook_entry.command == expected_cmd
    assert hook_entry.timeout == 30


def test_install_multiple_hooks(tmp_project: Path) -> None:
    """Test installing multiple hooks with different lifecycles."""
    # Define hooks
    hooks = [
        HookDefinition(
            id="hook-1",
            lifecycle="UserPromptSubmit",
            matcher="**",
            invocation="erk kit exec multi-kit hook-1",
            description="Hook 1",
            timeout=30,
        ),
        HookDefinition(
            id="hook-2",
            lifecycle="UserPromptSubmit",
            matcher="*.py",
            invocation="erk kit exec multi-kit hook-2",
            description="Hook 2",
            timeout=45,
        ),
        HookDefinition(
            id="hook-3",
            lifecycle="PostToolUse",
            matcher="**",
            invocation="erk kit exec multi-kit hook-3",
            description="Hook 3",
            timeout=60,
        ),
    ]

    # Install hooks
    count = install_hooks(
        kit_id="multi-kit",
        hooks=hooks,
        project_root=tmp_project,
    )

    # Verify count
    assert count == 3

    # Check settings structure
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None

    # Check user-prompt-submit lifecycle has 2 hooks
    submit_hooks = settings.hooks["UserPromptSubmit"]
    assert len(submit_hooks) == 2  # Two different matchers
    matchers = {group.matcher for group in submit_hooks}
    assert matchers == {"**", "*.py"}

    # Check PostToolUse lifecycle has 1 hook
    result_hooks = settings.hooks["PostToolUse"]
    assert len(result_hooks) == 1
    assert result_hooks[0].matcher == "**"


def test_install_hooks_missing_script(tmp_project: Path) -> None:
    """Test that all hooks are installed (no script validation anymore)."""
    hooks = [
        HookDefinition(
            id="exists",
            lifecycle="UserPromptSubmit",
            matcher="**",
            invocation="erk kit exec partial-kit exists",
            description="Exists",
            timeout=30,
        ),
        HookDefinition(
            id="missing",
            lifecycle="UserPromptSubmit",
            matcher="**",
            invocation="erk kit exec partial-kit missing",
            description="Missing",
            timeout=30,
        ),
    ]

    # Install hooks
    count = install_hooks(
        kit_id="partial-kit",
        hooks=hooks,
        project_root=tmp_project,
    )

    # Both hooks should be installed (no script validation)
    assert count == 2

    # Check settings has both hooks
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    lifecycle_hooks = settings.hooks["UserPromptSubmit"]
    assert len(lifecycle_hooks) == 1
    assert len(lifecycle_hooks[0].hooks) == 2


def test_install_hooks_replaces_same_hook_id(tmp_project: Path) -> None:
    """Test that installing a hook with same ID replaces the old one."""
    # First installation
    old_hook = HookDefinition(
        id="my-hook",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit v1",
        description="Version 1",
        timeout=30,
    )
    install_hooks("test-kit", [old_hook], tmp_project)

    # Second installation with same hook ID but different details
    new_hook = HookDefinition(
        id="my-hook",
        lifecycle="PostToolUse",  # Different lifecycle
        matcher="*.md",
        invocation="erk kit exec test-kit v2",
        description="Version 2",
        timeout=45,
    )
    count = install_hooks("test-kit", [new_hook], tmp_project)

    assert count == 1

    # Settings should only have the new version
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None

    # Old lifecycle should not have the hook
    if "UserPromptSubmit" in settings.hooks:
        for group in settings.hooks["UserPromptSubmit"]:
            for hook in group.hooks:
                assert "ERK_HOOK_ID=my-hook" not in hook.command

    # New lifecycle should have the hook
    assert "PostToolUse" in settings.hooks
    result_hooks = settings.hooks["PostToolUse"]
    assert len(result_hooks) == 1
    hook_entry = result_hooks[0].hooks[0]
    assert "ERK_HOOK_ID=my-hook" in hook_entry.command


def test_install_hooks_empty_list(tmp_project: Path) -> None:
    """Test installing with empty hooks list."""
    count = install_hooks(
        kit_id="empty-kit",
        hooks=[],
        project_root=tmp_project,
    )

    assert count == 0

    # Settings.json should not be created if it didn't exist
    settings_path = tmp_project / ".claude" / "settings.json"
    if settings_path.exists():
        load_settings(settings_path)
        # Should be empty or not have hooks from this kit
        # Note: With ERK_HOOK_ID format, we can't verify by kit_id since hooks
        # don't contain kit_id. An empty hooks list creates no entries anyway.


def test_install_hooks_creates_directories(tmp_project: Path) -> None:
    """Test that installation creates necessary directories."""
    # Start with no .claude directory
    claude_dir = tmp_project / ".claude"
    assert not claude_dir.exists()

    hook = HookDefinition(
        id="test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit test",
        description="Test",
        timeout=30,
    )

    install_hooks("test-kit", [hook], tmp_project)

    # .claude directory and settings should be created
    assert claude_dir.exists()
    assert (claude_dir / "settings.json").exists()


def test_install_hooks_flattens_nested_scripts(tmp_project: Path) -> None:
    """Test that invocation commands are used as-is (no script path handling)."""
    hook = HookDefinition(
        id="nested",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit nested",
        description="Nested",
        timeout=30,
    )

    install_hooks("test-kit", [hook], tmp_project)

    # Command should use the invocation with metadata
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    hook_entry = settings.hooks["UserPromptSubmit"][0].hooks[0]
    expected_cmd = "ERK_HOOK_ID=nested erk kit exec test-kit nested"
    assert hook_entry.command == expected_cmd


def test_remove_hooks_basic(tmp_project: Path) -> None:
    """Test removing hooks from a project."""
    # Install hooks first
    hook = HookDefinition(
        id="test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit test",
        description="Test",
        timeout=30,
    )
    install_hooks("test-kit", [hook], tmp_project)

    # Remove hooks by passing the hook definitions
    count = remove_hooks([hook], tmp_project)

    assert count == 1

    # Settings should not contain the hook
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    if settings.hooks is not None and "UserPromptSubmit" in settings.hooks:
        for group in settings.hooks["UserPromptSubmit"]:
            for hook_entry in group.hooks:
                assert "ERK_HOOK_ID=test" not in hook_entry.command


def test_remove_hooks_preserves_other_hooks(tmp_project: Path) -> None:
    """Test that removing one hook preserves other hooks."""
    # Install hooks from two kits
    hook_a = HookDefinition(
        id="hook-a",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec kit-a hook-a",
        description="A",
        timeout=30,
    )
    hook_b = HookDefinition(
        id="hook-b",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec kit-b hook-b",
        description="B",
        timeout=30,
    )

    install_hooks("kit-a", [hook_a], tmp_project)
    install_hooks("kit-b", [hook_b], tmp_project)

    # Remove only hook-a
    count = remove_hooks([hook_a], tmp_project)

    assert count == 1

    # Settings should only have hook-b
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    lifecycle_hooks = settings.hooks["UserPromptSubmit"]

    # Count hooks by hook_id
    hook_a_count = sum(
        1
        for group in lifecycle_hooks
        for hook in group.hooks
        if "ERK_HOOK_ID=hook-a" in hook.command
    )
    hook_b_count = sum(
        1
        for group in lifecycle_hooks
        for hook in group.hooks
        if "ERK_HOOK_ID=hook-b" in hook.command
    )

    assert hook_a_count == 0
    assert hook_b_count == 1


def test_remove_hooks_nonexistent_hook(tmp_project: Path) -> None:
    """Test removing hooks that were never installed."""
    # Create a hook definition that was never installed
    nonexistent_hook = HookDefinition(
        id="nonexistent",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit nonexistent",
        description="Never installed",
        timeout=30,
    )
    count = remove_hooks([nonexistent_hook], tmp_project)

    assert count == 0

    # Should not crash or create files
    tmp_project / ".claude" / "settings.json"
    # Just verify no crash


def test_remove_hooks_cleans_empty_lifecycles(tmp_project: Path) -> None:
    """Test that removing the last hook from a lifecycle removes the lifecycle."""
    hook = HookDefinition(
        id="test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit test",
        description="Test",
        timeout=30,
    )

    install_hooks("test-kit", [hook], tmp_project)
    remove_hooks([hook], tmp_project)

    # Settings should not have the lifecycle anymore
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    if settings.hooks is not None:
        assert (
            "UserPromptSubmit" not in settings.hooks or len(settings.hooks["UserPromptSubmit"]) == 0
        )


def test_hook_entry_metadata_roundtrip(tmp_project: Path) -> None:
    """Test that hook metadata survives JSON serialization roundtrip."""
    hook = HookDefinition(
        id="metadata-test",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec metadata-kit metadata-test",
        description="Metadata test",
        timeout=30,
    )

    install_hooks("metadata-kit", [hook], tmp_project)

    # Read raw JSON to check env vars in command
    settings_path = tmp_project / ".claude" / "settings.json"
    raw_json = settings_path.read_text(encoding="utf-8")
    # Note: hooks no longer contain ERK_KIT_ID, only ERK_HOOK_ID
    assert "ERK_HOOK_ID=metadata-test" in raw_json

    # Load and verify structure
    settings = load_settings(settings_path)
    assert settings.hooks is not None

    hook_entry = settings.hooks["UserPromptSubmit"][0].hooks[0]
    assert "ERK_HOOK_ID=metadata-test" in hook_entry.command

    # Re-save and re-load to ensure roundtrip works
    from erk.kits.hooks.settings import save_settings

    save_settings(settings_path, settings)
    reloaded_settings = load_settings(settings_path)

    assert reloaded_settings.hooks is not None
    reloaded_entry = reloaded_settings.hooks["UserPromptSubmit"][0].hooks[0]
    assert "ERK_HOOK_ID=metadata-test" in reloaded_entry.command


def test_install_hook_without_matcher(tmp_project: Path) -> None:
    """Test installing a hook without matcher field uses wildcard default."""
    # Define hook without matcher
    hook_def = HookDefinition(
        id="test-hook",
        lifecycle="UserPromptSubmit",
        invocation="erk kit exec test-kit test-hook",
        description="Test hook without matcher",
        timeout=30,
    )

    # Install hooks
    count = install_hooks(
        kit_id="test-kit",
        hooks=[hook_def],
        project_root=tmp_project,
    )

    # Verify installation
    assert count == 1

    # Check settings.json uses wildcard matcher
    settings_path = tmp_project / ".claude" / "settings.json"
    assert settings_path.exists()

    settings = load_settings(settings_path)
    assert settings.hooks is not None
    assert "UserPromptSubmit" in settings.hooks

    lifecycle_hooks = settings.hooks["UserPromptSubmit"]
    assert len(lifecycle_hooks) == 1
    assert lifecycle_hooks[0].matcher == "*"  # Should default to wildcard
    assert len(lifecycle_hooks[0].hooks) == 1

    hook_entry = lifecycle_hooks[0].hooks[0]
    assert "ERK_HOOK_ID=test-hook" in hook_entry.command


def test_install_hooks_includes_type_field(tmp_project: Path) -> None:
    """Test that installed hooks include a 'type' field for Claude Code compatibility.

    Claude Code requires hooks to have a 'type' discriminator field with value
    'command' or 'prompt'. This test ensures generated hooks are valid.
    """
    # Define hook
    hook_def = HookDefinition(
        id="test-hook",
        lifecycle="UserPromptSubmit",
        matcher="**",
        invocation="erk kit exec test-kit test-hook",
        description="Test hook",
        timeout=30,
    )

    # Install hooks
    count = install_hooks(
        kit_id="test-kit",
        hooks=[hook_def],
        project_root=tmp_project,
    )

    assert count == 1

    # Load settings and get hook entry
    settings = load_settings(tmp_project / ".claude" / "settings.json")
    assert settings.hooks is not None
    assert "UserPromptSubmit" in settings.hooks

    hook_entry = settings.hooks["UserPromptSubmit"][0].hooks[0]

    # Verify type field exists and has correct value
    assert hasattr(hook_entry, "type"), "Hook entry must have 'type' field for Claude Code"
    assert hook_entry.type == "command", "Hook type should be 'command' for shell commands"
