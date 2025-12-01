# Kit Code Architecture

## Two-Layer Architecture

Kit code lives in exactly TWO places:

### Layer 1: Canonical Implementation (erk-shared)

**Location**: `packages/erk-shared/src/erk_shared/integrations/[kit_name]/`

**What goes here**: All actual implementation code

```
packages/erk-shared/src/erk_shared/integrations/gt/
├── __init__.py                      # Public exports
├── abc.py                           # ABC interfaces
├── real.py                          # Real implementations
├── fake.py                          # Test fakes
├── types.py                         # Type definitions
├── prompts.py                       # Utilities
└── kit_cli_commands/
    └── gt/
        ├── submit_branch.py         # ACTUAL implementation (1000+ lines)
        ├── land_branch.py
        └── pr_update.py
```

**Rules**:

- ✅ All actual code goes here
- ❌ NO imports from `erk` package
- ❌ NO imports from `dot-agent-kit` package

### Layer 2: Kit Definition (dot-agent-kit)

**Location**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit_name]/`

**What goes here**: Kit metadata + thin shims (when needed, 10-20 lines each)

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/
├── kit.yaml                         # Kit metadata
├── kit_cli_commands/
│   └── gt/
│       └── land_pr.py               # Shim (imports from erk-shared)
├── agents/                          # Agent definitions
├── commands/                        # Command definitions
└── skills/                          # Skill definitions
```

**Rules**:

- ✅ Thin shims that re-export from erk-shared (when needed)
- ✅ Kit metadata (kit.yaml, agents/, commands/, skills/)
- ❌ NO actual implementation code
- ✅ Commands can be used directly from erk-shared without shims

**Example Shim**:

```python
# packages/dot-agent-kit/src/dot_agent_kit/data/kits/gt/kit_cli_commands/gt/land_pr.py
"""Re-export from erk-shared."""

from erk_shared.integrations.gt.kit_cli_commands.gt.land_pr import (
    land_pr,
)

__all__ = ["land_pr"]
```

## Architecture Diagram

```
┌───────────────────────────────────────┐
│ dot-agent-kit/data/kits/gt/           │
│   ├── kit.yaml                        │
│   └── kit_cli_commands/gt/            │
│       └── land_pr.py (shim)           │
│              ↓ imports                │
└───────────────────────────────────────┘
             ↓
┌───────────────────────────────────────┐
│ erk-shared/integrations/gt/           │
│   ├── abc.py                          │
│   ├── real.py                         │
│   ├── fake.py                         │
│   └── kit_cli_commands/gt/            │
│       ├── submit_branch.py (1000+loc) │
│       ├── pr_update.py                │
│       └── land_pr.py (core impl)      │
└───────────────────────────────────────┘
```

## Testing

Always import from erk-shared canonical locations:

```python
# ✅ CORRECT - Import from canonical submodules
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.kit_cli_commands.gt.submit_branch import pr_submit

# ❌ WRONG - Don't import from aggregation packages
from erk_shared.integrations.gt import RealGtKit

# ❌ WRONG - Don't import from kit location
from dot_agent_kit.data.kits.gt.kit_cli_commands.gt.submit_branch import pr_submit
```

## Validation Test

```python
def test_gt_kit_architecture() -> None:
    """Verify correct two-layer architecture."""

    # Layer 1: Implementation exists in erk-shared
    impl = Path("packages/erk-shared/src/erk_shared/integrations/gt/kit_cli_commands/gt/submit_branch.py")
    assert impl.exists()

    # Commands can be used directly from erk-shared
    # Shims are optional and only created when needed
```

## Quick Reference

**Q: Where do I put new kit command code?**
A: `packages/erk-shared/src/erk_shared/integrations/[kit_name]/kit_cli_commands/`

**Q: Where do I define the kit structure?**
A: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/[kit_name]/kit.yaml`

**Q: What goes in kit_cli_commands in dot-agent-kit?**
A: Optional thin shims (10-20 lines) that import from erk-shared. Most commands can be used directly from erk-shared without shims.

**Q: How do I know if code belongs in erk-shared?**
A: All implementation code goes in erk-shared. Only kit metadata (kit.yaml, agents/, commands/, skills/) and optional shims go in dot-agent-kit.
