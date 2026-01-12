# Documentation Plan: Hook Marker Detection Pattern

## Problem

The `ERK_HOOK_ID=` marker pattern for detecting hook versions is undocumented. This pattern enables:
- Fresh install vs needs-update vs current-version detection
- Safe hook replacement without losing user hooks
- Version-aware capability detection

## Context

Two distinct marker systems exist in erk:
1. **Worktree state markers** (documented in `markers.md`) - `.erk/scratch/__erk_markers/` for blocking operations
2. **Hook identity markers** (UNDOCUMENTED) - `ERK_HOOK_ID=` in hook commands for version detection

The pattern was just implemented in PR #4828 and should be documented.

## Key Files

- `src/erk/core/claude_settings.py` - Detection functions (`has_erk_hook_by_marker()`, `_is_erk_managed_hook()`)
- `src/erk/core/capabilities/hooks.py` - `HooksCapability.has_any_erk_hooks()` usage
- `docs/learned/architecture/capability-system.md` - Related capability docs
- `docs/learned/architecture/markers.md` - Related worktree markers docs

## Documentation Item

### Location
`docs/learned/architecture/hook-marker-detection.md`

### Action
Create new document

### Draft Content

```markdown
---
category: architecture
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
```

## Updates to Existing Docs

### `docs/learned/architecture/capability-system.md`
Add a "See Also" link to the new hook-marker-detection.md document in the hooks capability section.

### `docs/learned/index.md`
Add entry for hook-marker-detection.md under architecture category.

## Verification

1. Run `erk docs validate` to check frontmatter
2. Verify cross-links work
3. Check that `read_when` triggers are appropriate