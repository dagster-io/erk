---
title: Kit Code Architecture
read_when:
  - "understanding kit code structure"
  - "creating kit CLI commands"
  - "organizing kit Python code"
---

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
- ❌ NO imports from `erk-kits` package

### Layer 2: Kit Definition (erk-kits)

**Location**: `packages/erk-kits/src/erk_kits/data/kits/[kit_name]/`

**What goes here**: Kit metadata only (no code)

```
packages/erk-kits/src/erk_kits/data/kits/gt/
├── kit.yaml                         # Kit metadata
├── kit_cli_commands/
│   └── gt/
│       └── land_pr.py              # Direct implementation (no shims)
├── agents/                          # Agent definitions
├── commands/                        # Command definitions
└── skills/                          # Skill definitions
```

**Rules**:

- ✅ Kit metadata (kit.yaml, agents/, commands/, skills/)
- ✅ Kit CLI commands can be implemented directly (no need for shims)
- ❌ NO re-export shims (all re-exports have been eliminated)
- ❌ NO imports from `erk` package or `erk-kits` package

**Note**: Re-export shims (like `ops.py`, `real_ops.py`, `submit_branch.py`, `pr_update.py`, `prompts.py`) have been removed as part of the re-export elimination effort. All consumers now import directly from canonical sources in erk-shared.

## Architecture Diagram

```
┌───────────────────────────────────────┐
│ erk-kits/data/kits/gt/           │
│   ├── kit.yaml                        │
│   ├── agents/                         │
│   ├── commands/                       │
│   └── skills/                         │
└───────────────────────────────────────┘

┌───────────────────────────────────────┐
│ erk-shared/integrations/gt/           │
│   ├── abc.py                          │
│   ├── real.py                         │
│   ├── fake.py                         │
│   ├── types.py                        │
│   └── kit_cli_commands/gt/            │
│       ├── submit_branch.py            │
│       ├── land_pr.py                  │
│       └── pr_update.py                │
└───────────────────────────────────────┘
```

## Testing

Always import from erk-shared:

```python
# ✅ CORRECT - Import operations and types from erk-shared
from erk_shared.integrations.gt.real import RealGtKit
from erk_shared.integrations.gt.operations.preflight import execute_preflight
from erk_shared.integrations.gt.types import PreflightResult

# ❌ WRONG - don't import from kit location (CLI wrappers)
from erk_kits.data.kits.gt.kit_cli_commands.gt.submit_branch import pr_submit
```

## Validation Test

```python
def test_gt_kit_architecture() -> None:
    """Verify correct two-layer architecture."""

    # Layer 1: Operations exist in erk-shared
    ops = Path("packages/erk-shared/src/erk_shared/integrations/gt/operations/preflight.py")
    assert ops.exists()

    # Layer 2: CLI wrappers exist in erk-kits
    cli = Path("packages/erk-kits/src/erk_kits/data/kits/gt/kit_cli_commands/gt/submit_branch.py")
    assert cli.exists()

    # Layer 3: Kit metadata exists in erk-kits
    kit_yaml = Path("packages/erk-kits/src/erk_kits/data/kits/gt/kit.yaml")
    assert kit_yaml.exists()
```

## Quick Reference

**Q: Where do I put new kit command code?**
A: `packages/erk-shared/src/erk_shared/integrations/[kit_name]/kit_cli_commands/`

**Q: Where do I define the kit structure?**
A: `packages/erk-kits/src/erk_kits/data/kits/[kit_name]/kit.yaml`

**Q: What goes in kit_cli_commands in erk-kits?**
A: Only kit CLI commands that don't belong in erk-shared (very rare). Most kit CLI commands live in erk-shared.

**Q: How do I know if code belongs in erk-shared?**
A: If it has more than 20 lines of logic, it goes in erk-shared
