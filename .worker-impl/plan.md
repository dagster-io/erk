# Plan: Standardize Kit CLI Command Shim Pattern

## Problem

The `pr_prep` kit CLI command fails with "Command file not found" because:

- The implementation exists in `erk-shared` at `integrations/gt/kit_cli_commands/gt/pr_prep.py`
- But no corresponding shim file exists in `dot-agent-kit` at `data/kits/gt/kit_cli_commands/gt/pr_prep.py`
- The kit.yaml references the path, but the file is missing

## Solution

Add the missing shim file following the established pattern used by other gt kit commands.

## Implementation Steps

### Step 1: Create pr_prep.py shim

Create `/Users/schrockn/code/erk/packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/pr_prep.py`:

```python
"""Shim for pr_prep kit CLI command.

The canonical implementation is in erk_shared.integrations.gt.kit_cli_commands.gt.pr_prep.
This file exists only to provide the entry point for the kit CLI system.
Import symbols directly from the canonical location.
"""

from erk_shared.integrations.gt.kit_cli_commands.gt.pr_prep import (
    pr_prep as pr_prep,
)
```

### Step 2: Run tests to verify

Run the existing tests that already import from erk-shared:

- `packages/dot-agent-kit/tests/unit/kits/gt/test_pr_prep.py`

## Files to Modify

| File                                                                                   | Action            |
| -------------------------------------------------------------------------------------- | ----------------- |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/pr_prep.py` | Create (new shim) |

## Standard Practice Documentation

This establishes the standard pattern for kit CLI commands that call into erk-shared:

**Two-Artifact Pattern:**

1. **Canonical implementation** in `erk-shared/integrations/{kit}/kit_cli_commands/{kit}/{command}.py` - Contains all business logic
2. **Shim file** in `dot-agent-kit/data/kits/{kit}/kit_cli_commands/{kit}/{command}.py` - Re-exports the function

**Shim Template:**

```python
"""Shim for {command} kit CLI command.

The canonical implementation is in erk_shared.integrations.{kit}.kit_cli_commands.{kit}.{command}.
This file exists only to provide the entry point for the kit CLI system.
Import symbols directly from the canonical location.
"""

from erk_shared.integrations.{kit}.kit_cli_commands.{kit}.{command} import (
    {function_name} as {function_name},
)
```

## Out of Scope

- `get_pr_commit_message.py` - Currently only exists in dot-agent-kit. Could be migrated to follow this pattern in a future change if desired.
