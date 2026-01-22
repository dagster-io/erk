# Extract Branch Operations into Sub-Gateways

## Goal

Extract **mutation** branch operations from Git and Graphite gateways into separate sub-gateways (`GitBranchOps`, `GraphiteBranchOps`), making `BranchManager` the enforced abstraction for branch mutations. Read-only query methods stay on Git for convenience. This prevents accidental bypass of the BranchManager abstraction for operations that change state.

## Design Decision

- **Mutations** (create, delete, checkout, track) → Move to sub-gateways, only accessible through BranchManager
- **Queries** (get_current_branch, list_branches, etc.) → Stay on Git ABC for convenience

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   ErkContext                        │
│  ├── git: Git (queries only - NO mutations)         │
│  ├── graphite: Graphite (queries only - NO mutations)│
│  ├── github: GitHub                                 │
│  └── branch_manager: BranchManager ◄── MUTATIONS   │
└─────────────────────────────────────────────────────┘
                         │
         ┌───────────────┴───────────────┐
         ▼                               ▼
┌─────────────────────┐       ┌─────────────────────┐
│ GraphiteBranchManager│       │   GitBranchManager  │
│  (when Graphite on) │       │  (when Graphite off)│
└─────────────────────┘       └─────────────────────┘
         │                               │
    ┌────┴────┐                          │
    ▼         ▼                          ▼
┌────────┐ ┌──────────────┐       ┌────────────┐
│GitBranch│ │GraphiteBranch│       │GitBranchOps│
│  Ops   │ │    Ops       │       │  (internal)│
│(internal)│ │  (internal) │       └────────────┘
└────────┘ └──────────────┘
```

**Key Design Decision:** Sub-gateways are internal to BranchManager - NOT exposed on Git/Graphite ABCs. This makes bypass difficult.

---

## Phase 1: Create GitBranchOps Sub-Gateway

### 1.1 Create Package Structure

```
packages/erk-shared/src/erk_shared/git/branch_ops/
├── __init__.py
├── abc.py           # GitBranchOps ABC
├── real.py          # RealGitBranchOps
├── fake.py          # FakeGitBranchOps
├── dry_run.py       # DryRunGitBranchOps
└── printing.py      # PrintingGitBranchOps
```

### 1.2 GitBranchOps ABC Definition

Extract only **mutation methods** from Git ABC into `branch_ops/abc.py`:

**Mutation Methods (5 total):**
- `create_branch(cwd: Path, branch_name: str, start_point: str) -> None`
- `delete_branch(cwd: Path, branch_name: str, *, force: bool) -> None`
- `checkout_branch(cwd: Path, branch: str) -> None`
- `checkout_detached(cwd: Path, ref: str) -> None`
- `create_tracking_branch(repo_root: Path, branch: str, remote_ref: str) -> None`

**Query Methods (stay on Git ABC - NOT extracted):**
- `get_current_branch`, `list_local_branches`, `list_remote_branches`, etc. remain accessible via `ctx.git`

### 1.3 Implementation Files

**real.py** - Extract implementations from `RealGit` (packages/erk-shared/src/erk_shared/git/real.py)
**fake.py** - Extract implementations from `FakeGit` (packages/erk-shared/src/erk_shared/git/fake.py)
**dry_run.py** - Wrap GitBranchOps, no-op mutations, delegate queries
**printing.py** - Wrap GitBranchOps, print then delegate

---

## Phase 2: Create GraphiteBranchOps Sub-Gateway

### 2.1 Create Package Structure

```
packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/
├── __init__.py
├── abc.py           # GraphiteBranchOps ABC
├── real.py          # RealGraphiteBranchOps
├── fake.py          # FakeGraphiteBranchOps
├── dry_run.py       # DryRunGraphiteBranchOps
└── printing.py      # PrintingGraphiteBranchOps
```

### 2.2 GraphiteBranchOps ABC Definition

Extract only **mutation methods** from Graphite ABC into `branch_ops/abc.py`:

**Mutation Methods (3 total):**
- `track_branch(cwd: Path, branch_name: str, parent_branch: str) -> None`
- `delete_branch(repo_root: Path, branch: str) -> None`
- `submit_branch(repo_root: Path, branch_name: str, *, quiet: bool) -> None`

**Query Methods (stay on Graphite ABC - NOT extracted):**
- `is_branch_tracked`, `get_all_branches`, `get_branch_stack`, `get_parent_branch`, `get_child_branches` remain accessible via `ctx.graphite`

---

## Phase 3: Update BranchManager to Use Sub-Gateways

### 3.1 Update BranchManager Constructor Signatures

**GraphiteBranchManager** (packages/erk-shared/src/erk_shared/branch_manager/graphite.py):
```python
@dataclass(frozen=True)
class GraphiteBranchManager(BranchManager):
    git_branch_ops: GitBranchOps
    graphite_branch_ops: GraphiteBranchOps
    github: GitHub
```

**GitBranchManager** (packages/erk-shared/src/erk_shared/branch_manager/git.py):
```python
@dataclass(frozen=True)
class GitBranchManager(BranchManager):
    git_branch_ops: GitBranchOps
    github: GitHub
```

### 3.2 Add Factory Functions

Create `packages/erk-shared/src/erk_shared/git/branch_ops/factory.py`:
```python
def create_git_branch_ops(git: Git) -> GitBranchOps:
    """Extract GitBranchOps from a Git instance."""
    # Type-check and return appropriate implementation
```

Create `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/factory.py`:
```python
def create_graphite_branch_ops(graphite: Graphite) -> GraphiteBranchOps:
    """Extract GraphiteBranchOps from a Graphite instance."""
```

### 3.3 Update ErkContext.branch_manager Property

Update `packages/erk-shared/src/erk_shared/context/context.py`:
```python
@property
def branch_manager(self) -> BranchManager:
    git_branch_ops = create_git_branch_ops(self.git)

    if isinstance(self.graphite, GraphiteDisabled):
        return GitBranchManager(git_branch_ops=git_branch_ops, github=self.github)

    graphite_branch_ops = create_graphite_branch_ops(self.graphite)
    return GraphiteBranchManager(
        git_branch_ops=git_branch_ops,
        graphite_branch_ops=graphite_branch_ops,
        github=self.github,
    )
```

### 3.4 Extend BranchManager ABC

Add missing **mutation** methods to `packages/erk-shared/src/erk_shared/branch_manager/abc.py`:
- `checkout_branch(repo_root: Path, branch: str) -> None`
- `checkout_detached(repo_root: Path, ref: str) -> None`
- `create_tracking_branch(repo_root: Path, branch: str, remote_ref: str) -> None`

**Already exists on BranchManager:** `create_branch`, `delete_branch`, `track_branch`, `submit_branch`

**Query methods NOT added** - callers use `ctx.git` directly for queries like `get_current_branch`, `list_local_branches`, etc.

---

## Phase 4: Remove Mutation Methods from Git/Graphite ABCs

### 4.1 Remove from Git ABC (5 methods)

Remove only **mutation** methods from:
- `packages/erk-shared/src/erk_shared/git/abc.py`
- `packages/erk-shared/src/erk_shared/git/real.py`
- `packages/erk-shared/src/erk_shared/git/fake.py`
- `packages/erk-shared/src/erk_shared/git/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/printing.py`

Methods to remove: `create_branch`, `delete_branch`, `checkout_branch`, `checkout_detached`, `create_tracking_branch`

**Keep all query methods** on Git ABC (get_current_branch, list_local_branches, etc.)

### 4.2 Remove from Graphite ABC (3 methods)

Remove only **mutation** methods from:
- `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/real.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/fake.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/dry_run.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/printing.py`

Methods to remove: `track_branch`, `delete_branch`, `submit_branch`

**Keep all query methods** on Graphite ABC (is_branch_tracked, get_parent_branch, etc.)

---

## Phase 5: Migrate All Callers

### 5.1 High-Priority Files (Heavy Branch Usage)

| File | Changes Needed |
|------|----------------|
| `src/erk/cli/commands/submit.py` | 7 checkout, 1 create, 2 delete |
| `src/erk/cli/commands/wt/create_cmd.py` | 4 checkout, 1 create, 1 tracking |
| `src/erk/cli/commands/land_cmd.py` | 3 checkout |
| `src/erk/cli/commands/stack/move_cmd.py` | 6 checkout |
| `src/erk/cli/commands/branch/checkout_cmd.py` | 2 checkout, 1 tracking |
| `src/erk/cli/commands/branch/create_cmd.py` | 1 create |
| `src/erk/cli/commands/slot/common.py` | 2 checkout |
| `src/erk/cli/commands/admin.py` | 2 checkout |

### 5.2 Migration Pattern

```python
# MUTATIONS - migrate to BranchManager
# Before:
ctx.git.checkout_branch(repo_root, branch)
ctx.git.create_branch(repo_root, name, base)
ctx.git.delete_branch(repo_root, name, force=True)
ctx.git.create_tracking_branch(repo_root, branch, remote_ref)

# After:
ctx.branch_manager.checkout_branch(repo_root, branch)
ctx.branch_manager.create_branch(repo_root, name, base)
ctx.branch_manager.delete_branch(repo_root, name)
ctx.branch_manager.create_tracking_branch(repo_root, branch, remote_ref)

# QUERIES - stay on ctx.git (no change needed)
ctx.git.get_current_branch(cwd)  # Unchanged
ctx.git.list_local_branches(repo_root)  # Unchanged
```

### 5.3 Mutation Caller List (~20 files)

Files calling mutation methods that need migration:
- `src/erk/cli/commands/submit.py` - 7 checkout, 1 create, 2 delete
- `src/erk/cli/commands/wt/create_cmd.py` - 4 checkout, 1 create, 1 tracking
- `src/erk/cli/commands/land_cmd.py` - 3 checkout
- `src/erk/cli/commands/stack/move_cmd.py` - 6 checkout
- `src/erk/cli/commands/stack/consolidate_cmd.py` - checkout, delete
- `src/erk/cli/commands/branch/checkout_cmd.py` - 2 checkout, 1 tracking
- `src/erk/cli/commands/branch/create_cmd.py` - 1 create
- `src/erk/cli/commands/slot/common.py` - 2 checkout
- `src/erk/cli/commands/slot/init_pool_cmd.py` - 1 create
- `src/erk/cli/commands/slot/unassign_cmd.py` - checkout, create
- `src/erk/cli/commands/admin.py` - 2 checkout
- `src/erk/cli/commands/pr/checkout_cmd.py` - tracking
- `src/erk/cli/commands/plan/checkout_cmd.py` - tracking
- `src/erk/cli/commands/exec/scripts/setup_impl_from_issue.py` - checkout

**Query-only callers** (30+ files) - NO CHANGE NEEDED

---

## Phase 6: Update Test Infrastructure

### 6.1 Update FakeBranchManager

Add all new methods to `packages/erk-shared/src/erk_shared/branch_manager/fake.py` with mutation tracking.

### 6.2 Add Tests for Sub-Gateways

Create test files:
- `tests/unit/fakes/test_fake_git_branch_ops.py`
- `tests/unit/fakes/test_fake_graphite_branch_ops.py`

### 6.3 Update context_for_test()

Ensure `src/erk/core/context.py:context_for_test()` correctly creates sub-gateways.

---

## Phase 7: Update Tripwires

Add to `docs/learned/tripwires.md`:

```markdown
**CRITICAL: Before calling ctx.git mutation methods (create_branch, delete_branch, checkout_branch, checkout_detached, create_tracking_branch)** → Use ctx.branch_manager instead. Branch mutation methods have been removed from Git ABC. Query methods (get_current_branch, list_local_branches, etc.) are still available on ctx.git.

**CRITICAL: Before calling ctx.graphite mutation methods (track_branch, delete_branch, submit_branch)** → Use ctx.branch_manager instead. Branch mutation methods have been removed from Graphite ABC. Query methods (is_branch_tracked, get_parent_branch, etc.) are still available on ctx.graphite.
```

---

## Critical Files to Modify

### New Files to Create (12 files)
- `packages/erk-shared/src/erk_shared/git/branch_ops/__init__.py`
- `packages/erk-shared/src/erk_shared/git/branch_ops/abc.py`
- `packages/erk-shared/src/erk_shared/git/branch_ops/real.py`
- `packages/erk-shared/src/erk_shared/git/branch_ops/fake.py`
- `packages/erk-shared/src/erk_shared/git/branch_ops/dry_run.py`
- `packages/erk-shared/src/erk_shared/git/branch_ops/printing.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/__init__.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/abc.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/real.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/fake.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/dry_run.py`
- `packages/erk-shared/src/erk_shared/gateway/graphite/branch_ops/printing.py`

### Core Files to Modify
- `packages/erk-shared/src/erk_shared/git/abc.py` - Remove 5 mutation methods
- `packages/erk-shared/src/erk_shared/git/real.py` - Remove implementations
- `packages/erk-shared/src/erk_shared/git/fake.py` - Remove implementations
- `packages/erk-shared/src/erk_shared/git/dry_run.py` - Remove wrappers
- `packages/erk-shared/src/erk_shared/git/printing.py` - Remove wrappers
- `packages/erk-shared/src/erk_shared/gateway/graphite/abc.py` - Remove 3 mutation methods
- `packages/erk-shared/src/erk_shared/gateway/graphite/real.py` - Remove implementations
- `packages/erk-shared/src/erk_shared/gateway/graphite/fake.py` - Remove implementations
- `packages/erk-shared/src/erk_shared/gateway/graphite/dry_run.py` - Remove wrappers
- `packages/erk-shared/src/erk_shared/gateway/graphite/printing.py` - Remove wrappers
- `packages/erk-shared/src/erk_shared/branch_manager/abc.py` - Add 3 new methods (checkout_branch, checkout_detached, create_tracking_branch)
- `packages/erk-shared/src/erk_shared/branch_manager/graphite.py` - Update constructor, add methods
- `packages/erk-shared/src/erk_shared/branch_manager/git.py` - Update constructor, add methods
- `packages/erk-shared/src/erk_shared/branch_manager/fake.py` - Add new methods
- `packages/erk-shared/src/erk_shared/context/context.py` - Update branch_manager property

### Caller Migration (~20 files)
Files calling mutation methods (checkout, create, delete, tracking) on ctx.git or ctx.graphite. Query-only callers unchanged.

---

## Verification

1. **Type checking:** `make ty` passes
2. **Linting:** `make lint` passes
3. **Unit tests:** `make fast-ci` passes (4000+ tests)
4. **Integration tests:** `make all-ci` passes
5. **Manual test:** Run `erk submit` and `erk wt create` to verify branch operations work through BranchManager

---

## Execution Order

1. Phase 1 - Create GitBranchOps (independent)
2. Phase 2 - Create GraphiteBranchOps (independent)
3. Phase 3 - Update BranchManager (depends on 1 & 2)
4. Phase 5 - Migrate callers (can start after Phase 3)
5. Phase 4 - Remove from Git/Graphite ABCs (after all callers migrated)
6. Phase 6 - Update tests (throughout)
7. Phase 7 - Update tripwires (at end)