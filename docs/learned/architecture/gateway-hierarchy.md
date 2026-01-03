---
title: Gateway Hierarchy
read_when:
  - "understanding gateway relationships"
  - "deciding which gateway to use for an operation"
  - "understanding BranchManager abstraction"
  - "understanding GraphiteDisabled sentinel pattern"
---

# Gateway Hierarchy

Overview of erk's gateway architecture showing the layered abstraction from low-level primitives to high-level orchestration.

## Gateway Layers

```
┌─────────────────────────────────────────────────────────────────┐
│                    Higher-Level Abstractions                     │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                     BranchManager                            ││
│  │  Dual-mode branch operations (Graphite or plain Git)        ││
│  │  - get_pr_for_branch()  - Uses Graphite cache OR GitHub API ││
│  │  - create_branch()      - Uses gt create OR git branch      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Core Gateways (ABCs)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │     Git     │  │   GitHub    │  │  Graphite   │              │
│  │  Worktrees  │  │     PRs     │  │   Stacks    │              │
│  │  Branches   │  │   Labels    │  │  Parents    │              │
│  │  Commits    │  │  Comments   │  │  Submit     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│                                     (may be GraphiteDisabled)    │
└─────────────────────────────────────────────────────────────────┘
```

## Responsibility Boundaries

### Git Gateway (`erk_shared.git`)

**Responsibility**: Local repository operations

- Branch creation/deletion
- Worktree management (list, add, remove)
- Commit operations
- Remote detection (trunk branch discovery)

**When to use**: Any operation that only needs local git state.

### GitHub Gateway (`erk_shared.github`)

**Responsibility**: GitHub API operations

- PR creation, lookup, update
- Label management
- PR details and state queries

**When to use**: Operations requiring PR metadata or mutations.

### Graphite Gateway (`erk_shared.gateway.graphite`)

**Responsibility**: Graphite CLI wrapper and stack management

- Stack relationships (parent/child branches)
- Graphite-specific PR submission (`gt submit`)
- Restack/sync operations
- Branch tracking metadata

**When to use**: Stack-aware operations when Graphite is available.

**Note**: May be a `GraphiteDisabled` sentinel when Graphite is not installed or not enabled.

### BranchManager (`erk_shared.branch_manager`)

**Responsibility**: Dual-mode abstraction that works transparently regardless of Graphite availability

- `get_pr_for_branch()`: Uses Graphite's `.graphite_pr_info` cache (fast, no network) when available, falls back to GitHub REST API
- `create_branch()`: Uses `gt create` with Graphite or `git branch` without
- `is_graphite_managed()`: Check which mode is active

**When to use**: Operations that should work in both Graphite and plain-Git workflows.

## The GraphiteDisabled Sentinel Pattern

When Graphite is not available (not installed or disabled in config), the `graphite` field in `ErkContext` contains a `GraphiteDisabled` sentinel instead of `None`.

### Why a Sentinel?

Using `GraphiteDisabled` instead of `None` provides:

1. **Consistent type**: `ctx.graphite` is always `Graphite` type (no `| None`)
2. **Graceful degradation**: Read operations return empty results instead of crashing
3. **Clear errors**: Mutating operations raise `GraphiteDisabledError` with helpful messages

### How It Works

```python
@dataclass(frozen=True)
class GraphiteDisabled(Graphite):
    """Sentinel - implements Graphite ABC with degraded behavior."""
    reason: GraphiteDisabledReason

    # Read ops return empty/None (graceful degradation)
    def get_prs_from_graphite(self, ...) -> dict[str, PullRequestInfo]:
        return {}  # No PR info available

    # Mutating ops raise helpful errors
    def sync(self, repo_root, *, force, quiet) -> None:
        raise GraphiteDisabledError(self.reason)
```

### Checking for Graphite Availability

```python
from erk_shared.gateway.graphite.disabled import GraphiteDisabled

# Factory function pattern (recommended)
def create_branch_manager(git, github, graphite) -> BranchManager:
    if isinstance(graphite, GraphiteDisabled):
        return GitBranchManager(git=git, github=github)
    return GraphiteBranchManager(git=git, graphite=graphite)

# Direct check when needed
if isinstance(ctx.graphite, GraphiteDisabled):
    # Fall back to non-Graphite workflow
    ...
```

## Decision Tree: Which Gateway?

```
Need to work with PRs?
├── Yes → Need stack relationships?
│         ├── Yes → Is Graphite available?
│         │         ├── Yes → Use Graphite gateway
│         │         └── No  → Use GitHub gateway (no stack info)
│         └── No  → Use GitHub gateway directly
│
├── Need PR info that works with or without Graphite?
│   └── Use BranchManager.get_pr_for_branch()
│
└── No → Need worktree/branch ops?
         └── Use Git gateway directly
```

## BranchManager Factory Pattern

BranchManager uses factory dispatch to select the right implementation:

```python
# In factory.py
def create_branch_manager(git, github, graphite) -> BranchManager:
    if isinstance(graphite, GraphiteDisabled):
        return GitBranchManager(git=git, github=github)
    return GraphiteBranchManager(git=git, graphite=graphite)

# Consumer code doesn't know which implementation
branch_manager = create_branch_manager(ctx.git, ctx.github, ctx.graphite)
pr = branch_manager.get_pr_for_branch(repo_root, branch)
```

This pattern:

- Encapsulates the "which mode" decision
- Allows transparent switching based on Graphite availability
- Enables easy testing with fakes

## Related Topics

- [Gateway Inventory](gateway-inventory.md) - Complete list of all gateways
- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) - Adding new gateway methods
- [Protocol vs ABC](protocol-vs-abc.md) - Interface design decisions
