# Plan: Add Ruff Auto-Format Capability

> **Replans:** #4005

## What Changed Since Original Plan

The original plan proposed implementing the ruff auto-format hook as an exec script pattern. Since then:
- Erk now has a **capabilities system** (PRs #4563, #4555, #4554) for optional features that modify Claude Code settings
- The `HooksCapability` pattern shows exactly how to implement settings.json hook configuration
- Capabilities are the preferred approach for features that users opt into via `erk init capability add <name>`

## Remaining Work

The entire feature needs implementation - nothing from the original plan was built.

## Implementation Steps

### Step 1: Add helper functions to `claude_settings.py`

**File:** `src/erk/core/claude_settings.py`

Add:
```python
ERK_RUFF_FORMAT_HOOK_COMMAND = "uv run ruff format"

def has_ruff_format_hook(settings: Mapping[str, Any]) -> bool:
    """Check if ruff format PostToolUse hook is configured."""
    # Check for PostToolUse hook matching Write|Edit

def add_ruff_format_hook(settings: Mapping[str, Any]) -> dict[str, Any]:
    """Return new settings dict with ruff format PostToolUse hook added."""
    # Add PostToolUse entry for Write|Edit -> ruff format
```

The hook configuration should be:
```json
"PostToolUse": [
  {
    "matcher": "Write|Edit",
    "hooks": [
      {
        "type": "command",
        "command": "[[ \"${file_path}\" == *.py ]] && uv run ruff format \"${file_path}\" || true"
      }
    ]
  }
]
```

**Notes:**
- Use `${file_path}` template variable provided by Claude Code PostToolUse hooks
- Filter to `.py` files only using bash pattern matching
- `|| true` ensures non-Python files don't cause hook failure
- No exec script wrapper needed - direct shell command is sufficient

### Step 2: Create the capability

**File:** `src/erk/core/capabilities/ruff_format.py` (new file)

```python
"""Ruff format capability for auto-formatting Python files after Write/Edit."""

class RuffFormatCapability(Capability):
    name = "ruff-format"
    description = "Auto-format Python files with ruff after Write/Edit"
    scope = "project"
    installation_check_description = "PostToolUse ruff format hook in .claude/settings.json"
    artifacts = []  # settings.json is shared
    required = False  # optional capability

    def is_installed(self, repo_root: Path | None) -> bool:
        # Load settings.json, call has_ruff_format_hook()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        # Load settings.json, call add_ruff_format_hook(), write back
```

Follow the exact pattern from `HooksCapability` in `src/erk/core/capabilities/hooks.py`.

### Step 3: Register in the registry

**File:** `src/erk/core/capabilities/registry.py`

Add import and registration:
```python
from erk.core.capabilities.ruff_format import RuffFormatCapability

# In _all_capabilities():
RuffFormatCapability(),
```

### Step 4: Add tests

**File:** `tests/unit/core/capabilities/test_ruff_format.py` (new file)

Tests needed:
- `test_ruff_format_capability_name_and_description()`
- `test_is_installed_returns_false_when_no_settings()`
- `test_is_installed_returns_false_when_no_hook()`
- `test_is_installed_returns_true_when_hook_present()`
- `test_install_adds_hook_to_empty_settings()`
- `test_install_preserves_existing_hooks()`
- `test_install_idempotent_when_already_installed()`

**File:** `tests/unit/core/test_claude_settings.py` (modify)

Add tests for:
- `test_has_ruff_format_hook_returns_false_when_missing()`
- `test_has_ruff_format_hook_returns_true_when_present()`
- `test_add_ruff_format_hook_creates_post_tool_use_section()`
- `test_add_ruff_format_hook_preserves_existing_hooks()`

## Files to Create/Modify

| File | Action |
|------|--------|
| `src/erk/core/claude_settings.py` | Modify (add helper functions) |
| `src/erk/core/capabilities/ruff_format.py` | Create |
| `src/erk/core/capabilities/registry.py` | Modify (add import + registration) |
| `tests/unit/core/capabilities/test_ruff_format.py` | Create |
| `tests/unit/core/test_claude_settings.py` | Modify (add tests) |

## Usage After Implementation

```bash
# Install the capability
erk init capability add ruff-format

# Verify it's installed
erk init capability list
```

Once installed, any Write or Edit tool use on a `.py` file will automatically trigger `uv run ruff format` on that file.

## Verification

1. Run unit tests: `make test-unit`
2. Run type checker: `make ty`
3. Manual test:
   - In a test project, run `erk init capability add ruff-format`
   - Verify `.claude/settings.json` has the PostToolUse hook
   - Have Claude write a Python file with formatting issues
   - Verify the file is auto-formatted after the write

## Related Documentation

- Load `fake-driven-testing` skill for test patterns
- Reference `src/erk/core/capabilities/hooks.py` as the implementation template