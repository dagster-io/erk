---
title: Gateway Inventory
read_when:
  - "understanding available gateways"
  - "adding a new gateway"
last_audited: "2026-02-04 05:48 PT"
audit_result: edited
---

# Gateway Inventory

All gateways follow the ABC/Real/Fake pattern. Each lives under `packages/erk-shared/src/erk_shared/gateway/`.

## Discovering Gateways

Always discover the current list from source (this never drifts):

    find packages/erk-shared/src/erk_shared/gateway/ -name abc.py | sort

Read each gateway's `abc.py` for the authoritative method list and `fake.py` for test double capabilities.

## Implementation Layers

Each gateway has up to 5 files (`abc.py`, `real.py`, `fake.py`, `types.py`, `factory.py`). See [Gateway ABC Implementation](gateway-abc-implementation.md) for the full pattern description.

## When to Use Specific Gateways

- **Console** (`console/`): Use when commands need to prompt for user input or display rich output. Fake captures all output for assertion.
- **ClaudeInstallation** (`claude_installation/`): Use when accessing `~/.claude/projects/` for session logs. Abstracts path resolution and session discovery.
- **ErkInstallation** (`erk_installation/`): Use when accessing `.erk/` directory for scratch storage, config, or metadata. Abstracts repo root resolution.
- **CIRunner** (`ci_runner/`): Use when commands need to trigger or monitor GitHub Actions workflows.

## BranchManager

BranchManager (`branch_manager/`) abstracts Graphite vs plain Git branch operations. A factory at `branch_manager/factory.py` returns either `GraphiteBranchManager` or `GitBranchManager` based on Graphite availability. Read `abc.py` for the current method list.

## Sub-Gateway Extraction History

Sub-gateways under `git/` (e.g., `git/branch_ops/`, `git/worktree_ops/`, `git/config_ops/`) were extracted in phases from the monolithic `Git` ABC:

- **#6169 phases 3-8**: Extracted branch, worktree, and config operations into dedicated sub-gateways
- **#6190**: Extracted additional operations

This decomposition keeps each ABC focused and testable.

## AgentLauncher Gateway

**Purpose**: Abstract `os.execvp()` for launching Claude agent processes.

**Pattern**: 3-file simplified gateway (abc.py, real.py, fake.py) — no dry_run.py or printing.py

**Why simplified**: `os.execvp()` replaces the current process with no return (`NoReturn`). There's no return value to simulate in dry-run or print modes.

**Key characteristics**:

- **NoReturn type annotation**: Methods never return (process replacement)
- **Test strategy**: Fake implementation allows testing without actual process replacement
- **Integration points**: Used in 3 locations for Claude agent launches

**Implementation files**:

- `abc.py`: Abstract method with NoReturn annotation
- `real.py`: Calls `os.execvp()` directly
- `fake.py`: Records call and raises SystemExit for testing

**Code reference**: `packages/erk-shared/src/erk_shared/gateway/agent_launcher/`

**Related**: [Gateway ABC Implementation](gateway-abc-implementation.md) - 3-file simplified pattern section

## Adding a New Gateway

1. Create directory under `gateway/` with `abc.py`, `real.py`, `fake.py`
2. Add `types.py` if the gateway has result types
3. Add `factory.py` if instantiation requires logic
4. Wire into `ErkContext` (non-obvious step — check existing context setup)
5. Add tests using the fake

**Special case**: NoReturn operations (like `os.execvp()`) use 3-file simplified pattern — omit dry_run.py and printing.py
