---
title: Hook Marker Detection Pattern
read_when:
  - Adding a new hook managed by erk
  - Implementing version detection for artifacts
  - Understanding how hook updates work
---

# Hook Marker Detection Pattern

## Overview

Erk uses an `ERK_HOOK_ID=` marker pattern in hook commands to enable version-aware detection. This allows distinguishing between:

- **Fresh install**: No erk hooks present
- **Needs update**: Old hooks with marker but different command
- **Current version**: Exact command match

## The Marker Pattern

Erk hook commands embed an identifier as an environment variable prefix:

```python
ERK_USER_PROMPT_HOOK_COMMAND = "ERK_HOOK_ID=user-prompt-hook erk exec user-prompt-hook"
ERK_EXIT_PLAN_HOOK_COMMAND = "ERK_HOOK_ID=exit-plan-mode-hook erk exec exit-plan-mode-hook"
```

This marker persists even when the command after it changes, enabling detection of outdated hooks.

## Detection Functions

### `has_erk_hook_by_marker()`

Finds hooks by marker regardless of exact command version:

```python
has_erk_hook_by_marker(
    settings,
    hook_type="UserPromptSubmit",
    marker="ERK_HOOK_ID=user-prompt-hook",
    matcher=None,
)
```

### `_is_erk_managed_hook(command)`

Checks if any command contains the `ERK_HOOK_ID=` marker.

### `HooksCapability.has_any_erk_hooks()`

Uses marker detection to find any erk hooks (old or new).

## Three-Tier Detection Strategy

The `HooksCapability` uses this strategy:

1. `is_installed()` - Exact match on current command → "already configured"
2. `has_any_erk_hooks()` - Marker found → "Updated erk hooks"
3. Neither → "Added erk hooks" (fresh install)

## When to Use This Pattern

Use marker-based detection when:

- An artifact's content may change between versions
- You need to safely replace old versions without duplicating
- You want to distinguish update from fresh install in user messaging

## Related

- [Capability System](capability-system.md) - How capabilities track installation
- [Markers](markers.md) - Worktree state markers (different concept)
