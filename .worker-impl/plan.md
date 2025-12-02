# Plan: Move git and github Modules to erk-shared

## Overview

Move wrapper implementations from `src/erk/core/git/` and `src/erk/core/github/` to `packages/erk-shared/src/erk_shared/`, then update all imports across the codebase.

## Files to Move

### Git Module (3 files)

| Source | Destination |
|--------|-------------|
| `src/erk/core/git/dry_run.py` | `erk_shared/git/dry_run.py` |
| `src/erk/core/git/fake.py` | `erk_shared/git/fake.py` |
| `src/erk/core/git/printing.py` | `erk_shared/git/printing.py` |

### GitHub Module (4 files)

| Source | Destination |
|--------|-------------|
| `src/erk/core/github/dry_run.py` | `erk_shared/github/dry_run.py` |
| `src/erk/core/github/printing.py` | `erk_shared/github/printing.py` |
| `src/erk/core/github/issue_link_branches_dry_run.py` | `erk_shared/github/issue_link_branches_dry_run.py` |
| `src/erk/core/github/issue_link_branches_real.py` | `erk_shared/github/issue_link_branches_real.py` |

### Files to Delete (deprecated shims)

- `src/erk/core/github/fake.py` - re-export shim (FakeGitHub already in erk_shared)
- `src/erk/core/github/real.py` - re-export shim (RealGitHub already in erk_shared)

## Import Changes

**59 files** import from `erk.core.git`:
- Pattern: `from erk.core.git.fake import FakeGit` (65 occurrences)
- Pattern: `from erk.core.git.dry_run import DryRunGit` (9 occurrences)

**4 files** import from `erk.core.github`:
- Pattern: `from erk.core.github.dry_run import DryRunGitHub`
- Pattern: `from erk.core.github.issue_link_branches_*`

**Key observation**: Files being moved already import from `erk_shared` internally, so no internal modifications needed.

## Implementation Steps

### Step 1: Move git files to erk-shared

1. Copy `src/erk/core/git/dry_run.py` → `packages/erk-shared/src/erk_shared/git/dry_run.py`
2. Copy `src/erk/core/git/fake.py` → `packages/erk-shared/src/erk_shared/git/fake.py`
3. Copy `src/erk/core/git/printing.py` → `packages/erk-shared/src/erk_shared/git/printing.py`

### Step 2: Move github files to erk-shared

1. Copy `src/erk/core/github/dry_run.py` → `packages/erk-shared/src/erk_shared/github/dry_run.py`
2. Copy `src/erk/core/github/printing.py` → `packages/erk-shared/src/erk_shared/github/printing.py`
3. Copy `src/erk/core/github/issue_link_branches_dry_run.py` → `packages/erk-shared/src/erk_shared/github/issue_link_branches_dry_run.py`
4. Copy `src/erk/core/github/issue_link_branches_real.py` → `packages/erk-shared/src/erk_shared/github/issue_link_branches_real.py`

### Step 3: Update erk_shared __init__.py files

Update `packages/erk-shared/src/erk_shared/git/__init__.py` to export new implementations.

Update `packages/erk-shared/src/erk_shared/github/__init__.py` to export new implementations.

### Step 4: Update all imports across codebase

Replace import patterns:
```python
# Git
from erk.core.git.fake import FakeGit      → from erk_shared.git.fake import FakeGit
from erk.core.git.dry_run import DryRunGit → from erk_shared.git.dry_run import DryRunGit

# GitHub
from erk.core.github.dry_run import DryRunGitHub → from erk_shared.github.dry_run import DryRunGitHub
from erk.core.github.issue_link_branches_dry_run import DryRunIssueLinkBranches → from erk_shared.github.issue_link_branches_dry_run import DryRunIssueLinkBranches
from erk.core.github.issue_link_branches_real import RealIssueLinkBranches → from erk_shared.github.issue_link_branches_real import RealIssueLinkBranches
```

Key files to update:
- `src/erk/core/context.py` (production)
- `tests/fakes/context.py`
- `packages/dot-agent-kit/src/dot_agent_kit/context.py`
- ~56 test files

### Step 5: Delete old directories

1. Remove all files from `src/erk/core/git/`
2. Remove all files from `src/erk/core/github/`
3. Delete `src/erk/core/git/` directory
4. Delete `src/erk/core/github/` directory

### Step 6: Verify

1. Run pyright to check types
2. Run pytest to verify tests pass
3. Grep for any remaining old imports

## Critical Files

- `src/erk/core/context.py` - main production consumer
- `packages/erk-shared/src/erk_shared/git/__init__.py` - update exports
- `packages/erk-shared/src/erk_shared/github/__init__.py` - update exports