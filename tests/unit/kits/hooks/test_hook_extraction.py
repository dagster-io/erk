"""Tests for hook ID extraction from settings.json commands."""

from erk.cli.commands.kit.check import _extract_hooks_for_kit
from erk.kits.hooks.models import ClaudeSettings, HookDefinition, HookEntry, MatcherGroup


def test_extract_hooks_extracts_hook_id_from_command() -> None:
    """Test that hook ID is correctly extracted from ERK_HOOK_ID env var.

    This is a regression test for the bug where _extract_hooks_for_kit would
    use kit_id as fallback instead of extracting the actual hook ID from the
    ERK_HOOK_ID environment variable in the command string.
    """
    # Setup: Create settings with a hook that has ERK_HOOK_ID
    hook_entry = HookEntry(
        type="command",
        command=(
            "ERK_KIT_ID=my-kit ERK_HOOK_ID=my-hook "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/script.py"'
        ),
        timeout=30,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook_entry],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Define expected hooks for validation
    expected_hooks = [
        HookDefinition(
            id="my-hook",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation='python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/script.py"',
            description="Test hook",
            timeout=30,
        )
    ]

    # Execute: Extract hooks for "my-kit"
    extracted_hooks = _extract_hooks_for_kit(settings, "my-kit", expected_hooks)

    # Verify: Should extract "my-hook" as hook_id, NOT "my-kit"
    assert len(extracted_hooks) == 1, "Should extract one hook"
    assert extracted_hooks[0].hook_id == "my-hook", (
        f"Expected hook_id 'my-hook', got '{extracted_hooks[0].hook_id}'. "
        "Hook ID should be extracted from ERK_HOOK_ID env var, not fallback to kit_id"
    )
    assert extracted_hooks[0].lifecycle == "UserPromptSubmit"
    assert extracted_hooks[0].timeout == 30


def test_extract_hooks_fails_without_hook_id() -> None:
    """Test that extraction fails hard when ERK_HOOK_ID is missing.

    Old format commands that don't have ERK_HOOK_ID should cause an error,
    not silently fall back to using kit_id as hook_id.
    """
    # Setup: Create settings with old format (no ERK_HOOK_ID)
    hook_entry = HookEntry(
        type="command",
        command=('ERK_KIT_ID=my-kit python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/script.py"'),
        timeout=30,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook_entry],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Execute & Verify: Should raise ValueError for old format
    try:
        _extract_hooks_for_kit(settings, "my-kit", [])
        raise AssertionError("Should have raised ValueError for missing ERK_HOOK_ID")
    except ValueError as e:
        assert "ERK_HOOK_ID" in str(e), "Error should mention missing ERK_HOOK_ID"


def test_extract_hooks_handles_multiple_hooks_for_same_kit() -> None:
    """Test extraction of multiple hooks from the same kit."""
    # Setup: Create settings with multiple hooks
    hook1 = HookEntry(
        type="command",
        command=(
            "ERK_KIT_ID=my-kit ERK_HOOK_ID=hook-1 "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/h1.py"'
        ),
        timeout=30,
    )
    hook2 = HookEntry(
        type="command",
        command=(
            "ERK_KIT_ID=my-kit ERK_HOOK_ID=hook-2 "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/h2.py"'
        ),
        timeout=60,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook1, hook2],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Define expected hooks for validation
    expected_hooks = [
        HookDefinition(
            id="hook-1",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation='python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/h1.py"',
            description="Hook 1",
            timeout=30,
        ),
        HookDefinition(
            id="hook-2",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation='python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/my-kit/h2.py"',
            description="Hook 2",
            timeout=60,
        ),
    ]

    # Execute: Extract hooks for "my-kit"
    extracted_hooks = _extract_hooks_for_kit(settings, "my-kit", expected_hooks)

    # Verify: Should extract both hooks with correct IDs
    assert len(extracted_hooks) == 2, "Should extract two hooks"

    hook_ids = {hook.hook_id for hook in extracted_hooks}
    assert hook_ids == {"hook-1", "hook-2"}, f"Expected hook IDs {{hook-1, hook-2}}, got {hook_ids}"


def test_extract_hooks_ignores_other_kits() -> None:
    """Test that extraction only returns hooks for the specified kit."""
    # Setup: Create settings with hooks from different kits
    hook1 = HookEntry(
        type="command",
        command=(
            "ERK_KIT_ID=kit-a ERK_HOOK_ID=hook-a "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/kit-a/script.py"'
        ),
        timeout=30,
    )
    hook2 = HookEntry(
        type="command",
        command=(
            "ERK_KIT_ID=kit-b ERK_HOOK_ID=hook-b "
            'python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/kit-b/script.py"'
        ),
        timeout=30,
    )

    hook_group = MatcherGroup(
        matcher="*",
        hooks=[hook1, hook2],
    )

    settings = ClaudeSettings(
        permissions=None,
        hooks={
            "UserPromptSubmit": [hook_group],
        },
    )

    # Define expected hooks for validation
    expected_hooks = [
        HookDefinition(
            id="hook-a",
            lifecycle="UserPromptSubmit",
            matcher="*",
            invocation='python3 "$CLAUDE_PROJECT_DIR/.claude/hooks/kit-a/script.py"',
            description="Hook A",
            timeout=30,
        ),
    ]

    # Execute: Extract hooks for "kit-a" only
    extracted_hooks = _extract_hooks_for_kit(settings, "kit-a", expected_hooks)

    # Verify: Should only extract hook-a
    assert len(extracted_hooks) == 1, "Should extract only one hook for kit-a"
    assert extracted_hooks[0].hook_id == "hook-a"
