---
title: Gastown Architecture Analysis
read_when:
  - "learning from parallel agent orchestration systems"
  - "designing multi-agent coordination"
  - "understanding propulsion-based agent patterns"
  - "comparing erk to other agentic systems"
---

# Gastown Architecture Analysis

> **Point-in-Time Snapshot**
>
> - **Commit:** `b158ff27c25efa02ad2a6948a923186a99c6a429`
> - **Version:** v0.5.0
> - **Captured:** 2026-01-21
>
> Gastown evolves rapidly. This document captures architecture and patterns at a specific point for cross-pollination learning. For current state, consult the Gastown repository directly.

## Executive Summary

Gastown is a multi-agent orchestration system that coordinates AI agents across multiple isolated workspaces ("rigs") within a "town." Unlike polling-based systems, Gastown uses a **propulsion principle** where agents actively drive work forward upon discovering it on their hook, following a "physics over politeness" philosophy.

This document exists to capture learnings from Gastown's parallel approach to agentic engineering, identifying patterns that could strengthen Erk and areas where each system excels.

## Core Philosophy

### Steam Engine Metaphor

Gastown models agents as **pistons in a steam engine**. Each agent:

- Has a defined role and stroke pattern
- Fires when pressure builds (work accumulates)
- Drives the crankshaft (overall progress) through coordinated action
- Self-maintains position in the engine cycle

The town is the engine housing. Rigs are cylinder banks. Agents are pistons.

### Propulsion Principle

The defining characteristic of Gastown:

> **"If you find work on your hook, YOU RUN IT."**

This means:

- Agents don't wait for instructions after discovering work
- No announcement/confirmation loops
- No polling or asking "should I do this?"
- Work ownership transfers on hook attachment

**Example flow:**

1. Work appears on Polecat's hook
2. Polecat immediately begins execution
3. Polecat completes and calls `gt done`
4. Hook releases, Polecat self-terminates

**Anti-patterns to avoid:**

- Polling for work availability
- Announcing "I found work, shall I proceed?"
- Waiting for confirmation before acting
- Checking work status repeatedly

### Physics Over Politeness

Agents operate on mechanical principles, not social conventions:

- State transitions happen automatically when conditions are met
- Timeouts trigger escalations without asking
- Redundant observers ensure convergence
- Attribution is mechanical, not ceremonial

### Attribution as First-Class Concern

Every action in Gastown carries provenance:

- `BD_ACTOR` environment variable tracks the current agent
- Commits attribute to the acting agent
- Audit trails are automatic, not opt-in
- Blame flows through the system mechanically

## Architecture Overview

### Town Structure

```
town/
├── .gastown/           # Town configuration
│   ├── config.toml     # Town-level settings
│   ├── mayor/          # Mayor agent state
│   └── deacon/         # Deacon daemon state
├── rigs/               # All project rigs
│   ├── project-a/      # Individual rig
│   │   ├── .rig/       # Rig configuration
│   │   ├── refinery/   # Merge queue state
│   │   ├── witness/    # Health monitor state
│   │   └── polecats/   # Worker pool
│   └── project-b/
└── beads/              # Town-level ledger
    ├── town.jsonl      # Town bead ledger
    └── archives/       # Historical digests
```

### Two-Level Beads Architecture

Gastown maintains ledgers at two levels:

1. **Town-level beads:** Cross-rig coordination, escalations, convoys
2. **Rig-level beads:** Project-specific issues, work items, molecules

This separation allows:

- Isolation of project concerns
- Town-wide visibility for coordination
- Efficient querying within scope

### Component Hierarchy

```
                    ┌─────────┐
                    │  Mayor  │  Town-level coordinator
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────▼────┐ ┌───▼───┐ ┌────▼────┐
         │ Deacon  │ │ Boot  │ │  Mail   │
         └────┬────┘ └───┬───┘ └─────────┘
              │          │
    ┌─────────┼──────────┼─────────┐
    │         │          │         │
┌───▼───┐ ┌───▼───┐ ┌────▼────┐ ┌──▼──┐
│Witness│ │Refinery│ │ Polecat │ │ ... │
└───────┘ └────────┘ └─────────┘ └─────┘
   Per-rig agents          Ephemeral workers
```

## Core Abstractions

### Town

The top-level container for all Gastown operations.

**What it is:**

- A directory structure containing rigs, configuration, and town-level state
- The coordination boundary for multi-rig operations
- Home to town-level agents (Mayor, Deacon)

**Directory structure:**

- `.gastown/` - Town configuration and agent state
- `rigs/` - Container for all project rigs
- `beads/` - Town-level ledger files

**Configuration files:**

- `config.toml` - Town-level settings (rig paths, agent configs, escalation routes)
- Agent-specific state directories

### Rigs

Project containers providing workspace isolation.

**What they are:**

- Isolated workspaces for individual projects
- Contain their own bead ledger, agents, and configuration
- Can operate independently or coordinate via town

**Rig components:**

- `mayor/` - Rig-level coordination (inherits from town Mayor)
- `refinery/` - Merge queue processor state
- `witness/` - Health monitor state
- `crew/` - Persistent agents assigned to this rig
- `polecats/` - Ephemeral worker pool

**Rig-level beads:**

- Project-specific issues and work items
- Molecule instances tracking workflow progress
- Local escalations before town-level routing

### Agents

#### Mayor

**Role:** Town-level coordinator

**Responsibilities:**

- Dispatches work across rigs
- Manages town-level beads
- Coordinates cross-rig operations
- Handles escalation routing

**Lifecycle:** Long-running, persistent state

#### Deacon

**Role:** Background daemon with patrol cycles

**Responsibilities:**

- Performs periodic health checks
- Detects stale work items
- Triggers auto-escalations
- Maintains heartbeat across rigs

**Lifecycle:** Always running, periodic wake cycles

**Patrol pattern:**

1. Wake on schedule (cron or interval)
2. Survey all rigs for health indicators
3. Identify stale/stuck items
4. Escalate or remediate as configured
5. Return to sleep

#### Boot

**Role:** Ephemeral triage agent

**Responsibilities:**

- Fresh context on every tick (no accumulated state)
- Triages incoming work
- Routes to appropriate agent/rig
- Quick decisions, no long-running tasks

**Lifecycle:** Ephemeral per-tick, destroyed after triage

**Design rationale:** By starting fresh each tick, Boot avoids context pollution and makes consistent triage decisions.

#### Witness

**Role:** Per-rig health monitor

**Responsibilities:**

- Monitors rig-level health indicators
- Reports anomalies to Deacon
- Tracks molecule progress
- First responder for rig issues

**Lifecycle:** Long-running, per-rig instance

#### Refinery

**Role:** Per-rig merge queue processor

**Responsibilities:**

- Manages PR merge queue for the rig
- Ensures merge order and dependencies
- Handles merge conflicts and retries
- Reports status to Witness

**Lifecycle:** Long-running, per-rig instance

#### Polecats

**Role:** Ephemeral worker agents

**Responsibilities:**

- Execute assigned work items
- Self-terminate on completion
- No persistent state between invocations
- Follow propulsion principle strictly

**Lifecycle:** Ephemeral per-task

**Hook workflow:**

1. Work appears on hook (via `gt sling`)
2. Polecat spawns and attaches
3. Executes work following instructions
4. Calls `gt done` on completion
5. Self-terminates

### Beads (Ledger System)

Git-backed JSONL issue tracking.

**What beads are:**

- Individual tracked items (issues, tasks, molecules)
- Stored in JSONL format for git-friendly diffs
- Queryable via `gt` commands
- Source of truth for work state

**Bead anatomy:**

```jsonl
{
  "id": "bead-123",
  "type": "issue",
  "status": "open",
  "labels": [
    "bug"
  ],
  "description": "Fix login timeout",
  "created": "2026-01-20T10:00:00Z"
}
```

**Key fields:**

- `id` - Unique bead identifier
- `type` - Bead type (issue, molecule, escalation, etc.)
- `status` - Current state (open, in_progress, closed)
- `labels` - Classification labels
- `description` - Human-readable description

**Wisps:**

Ephemeral entries that accumulate and squash to digests:

- High-frequency updates (progress, heartbeats)
- Squashed periodically to maintain ledger efficiency
- Digests preserve important state changes
- Prevents ledger bloat from fine-grained updates

**Cross-rig references:**

Beads can reference beads in other rigs:

```jsonl
{
  "id": "bead-456",
  "refs": [
    "rig-a:bead-123",
    "rig-b:bead-789"
  ]
}
```

### Hooks

Work assignment mechanism implementing the propulsion principle.

**What hooks are:**

- Points of work attachment for agents
- Transfer ownership on attachment
- Clear lifecycle (pin, execute, done)
- Enforce propulsion ("if hooked, run it")

**Hook lifecycle:**

1. **Pin** - Work is pinned to a hook via `gt sling <target>`
2. **Attach** - Agent discovers and attaches to hooked work
3. **Execute** - Agent performs work (propulsion principle applies)
4. **Done** - Agent completes and releases hook via `gt done`

**Relation to propulsion:**

Hooks are the mechanical enforcement of propulsion. When an agent's hook has work, the agent must act. No waiting, no asking.

### Molecules & Formulas

Workflow automation system.

**Formulas:**

TOML templates defining workflow steps:

```toml
[formula]
name = "feature-development"
description = "Standard feature development workflow"

[[steps]]
name = "implement"
agent = "polecat"
gate = "manual"

[[steps]]
name = "test"
agent = "polecat"
gate = "previous_complete"

[[steps]]
name = "review"
agent = "witness"
gate = "tests_pass"
```

**Protomolecules:**

Frozen formulas ready to instantiate:

- Validated formula definition
- All dependencies resolved
- Ready for `gt molecule create`

**Molecules:**

Active workflow instances:

- Created from protomolecules
- Track current step and state
- Have associated step beads
- Progress via `bd close --continue`

**Step transitions:**

The `bd close --continue` command:

1. Closes current step bead
2. Evaluates next step's gate condition
3. Opens next step if gate passes
4. Updates molecule state

### Convoys

Batch work tracking for coordinated multi-item operations.

**What convoys are:**

- Group multiple related work items
- Track collective progress
- Auto-complete when all items finish
- Coordinate swarm workers

**Swarm concept:**

Multiple Polecats working on convoy items:

- Each Polecat handles one item
- Convoy tracks aggregate progress
- Completion triggers when last item finishes
- No central coordinator needed (event-driven)

**Auto-completion:**

Convoys detect completion without polling:

1. Each item completion updates convoy state
2. Convoy checks remaining items
3. When count reaches zero, convoy closes
4. Downstream beads notified

### Mail System

Inter-agent messaging for coordination.

**Components:**

- **Inbox** - Pending messages for agent
- **Outbox** - Sent messages from agent
- **Priority levels** - Urgent, normal, low

**Message flow:**

1. Agent A sends via `gt mail send <target> <message>`
2. Message appears in target's inbox
3. Target processes on next check
4. Acknowledgment optional

**Priority routing:**

- Urgent: Interrupts current work
- Normal: Processed in order
- Low: Batched processing

### Escalation System

Severity-based routing when agents get stuck.

**Severity levels:**

- **Critical** - Immediate attention, blocks progress
- **High** - Urgent but not blocking
- **Medium** - Should address soon
- **Low** - Track for later

**Routing configuration:**

Escalations route based on:

- Severity level
- Rig/town scope
- Agent capabilities
- Current load

**Stale detection:**

Automatic re-escalation for unacknowledged issues:

1. Escalation created with timeout
2. If not acknowledged within timeout, severity increases
3. Re-routes to higher-level handler
4. Continues until acknowledged

**Acknowledgment and closure:**

- `gt escalate ack <id>` - Acknowledge, take ownership
- `gt escalate close <id>` - Resolve and close
- Acknowledgment stops re-escalation timer

## Key Design Patterns

### Propulsion Principle (Detailed)

The propulsion principle is Gastown's defining pattern.

**Core rule:**

> When an agent discovers work on its hook, it immediately begins execution without waiting for confirmation.

**Why it matters:**

- Eliminates round-trip latency for confirmations
- Prevents deadlocks from mutual waiting
- Ensures work progresses when discovered
- Simplifies agent logic (no decision points)

**Implementation:**

```
Agent loop:
1. Check hook for work
2. If work found:
   a. Attach to work (ownership transfers)
   b. Execute work to completion
   c. Call `gt done`
   d. Self-terminate (for Polecats)
3. If no work: sleep/poll (for persistent agents)
```

**Anti-patterns and their costs:**

| Anti-pattern           | Cost                       |
| ---------------------- | -------------------------- |
| Announcing before work | 2x latency, potential race |
| Polling for permission | Wasted cycles, delays      |
| Confirmation loops     | Deadlock risk, complexity  |
| Status checking        | Stale state, races         |

**When propulsion applies:**

- Hooked work: Always
- Mail messages: By priority (urgent = propulsion)
- Escalations: Always for critical severity

### Event-Driven Completion

Work completion is detected through events, not polling.

**How convoys detect completion:**

1. Item finishes → Updates convoy bead
2. Convoy bead tracks remaining count
3. Count reaches zero → Convoy closes automatically
4. No periodic "are we done yet?" checks

**Redundant monitoring:**

Multiple observers ensure convergence:

- **Deacon** - Periodic sweeps catch missed events
- **Witness** - Rig-level monitoring catches local issues
- **Refinery** - Merge queue tracks PR state

If one observer misses an event, another will catch it on next cycle.

**Benefits:**

- Lower latency than polling
- Scales with work items (not observer count)
- Self-healing through redundancy

### Separation of Transport/Triage/Execution

Gastown separates concerns across agent types.

**Daemon (Go, mechanical heartbeat):**

- Pure infrastructure
- No AI/decision-making
- Reliable scheduling
- Process management

**Boot (ephemeral AI, fresh context):**

- Triage and routing only
- Fresh context each tick
- No accumulated state
- Quick decisions

**Deacon (long-running agent):**

- Pattern recognition over time
- Historical context
- Complex decisions
- Escalation handling

**Why separate:**

- Boot's fresh context prevents bias accumulation
- Deacon's history enables trend detection
- Daemon's simplicity ensures reliability
- Each optimized for its role

### Reality-First State

Query observables, not metadata.

**Principle:**

- Git working tree is truth, not bead status
- File existence beats claimed state
- External APIs are authoritative
- Metadata is a cache, not source

**Example:**

```
# Wrong: Trust bead says PR is open
pr_state = bead.get("pr_status")  # Could be stale

# Right: Query GitHub for actual state
pr_state = gh_api.get_pr(number).state  # Authoritative
```

**When to use metadata:**

- Performance optimization (cache)
- Historical analysis (what was claimed)
- Audit trails (what we believed)

**When to query reality:**

- Before acting on state
- When making decisions
- After significant time gaps

### Attribution & Provenance

Every action carries actor information.

**BD_ACTOR environment variable:**

Set before any agent action:

```bash
export BD_ACTOR="polecat-abc123"
git commit -m "Fix bug" --author="$BD_ACTOR <noreply@gastown>"
```

**Commit attribution:**

All commits attribute to the acting agent:

- Author set from BD_ACTOR
- Commit message includes agent context
- Allows tracing who did what

**Audit trails:**

- Bead modifications track actor
- State changes include provenance
- Escalations record handler chain

## Concept Mapping: Gastown to Erk

| Gastown    | Erk                | Notes                                                   |
| ---------- | ------------------ | ------------------------------------------------------- |
| Town       | (no equivalent)    | Erk is single-workspace focused                         |
| Rig        | Worktree           | Both provide workspace isolation                        |
| Polecat    | Agent in worktree  | Both are ephemeral workers                              |
| Mayor      | Planning phase     | Both coordinate high-level direction                    |
| Convoy     | Objective          | Both track multi-PR coordinated work                    |
| Beads      | Markers + sessions | Both persist state across sessions                      |
| Molecules  | Plan steps         | Both structure multi-step workflows                     |
| Hook       | (partial: markers) | Erk markers track state but don't enforce propulsion    |
| Escalation | (missing)          | Critical gap - Erk lacks severity-based routing         |
| Mail       | (missing)          | Critical gap - No formal inter-agent messaging          |
| Deacon     | (missing)          | Critical gap - No background health monitoring daemon   |
| Boot       | (no equivalent)    | Erk doesn't separate triage from execution              |
| Refinery   | Graphite/gt        | Both manage PR merge queues                             |
| Witness    | (partial: CI)      | CI provides some health checking, not agent-driven      |
| Wisps      | (no equivalent)    | Erk doesn't have ephemeral-to-digest pattern            |
| Formulas   | Plan templates     | Both define reusable workflow patterns                  |
| BD_ACTOR   | Session ID         | Both track provenance, different granularity            |
| Propulsion | (weak: plan mode)  | Plan mode implements partial propulsion for saved plans |

## Learnings for Erk

### Critical Gaps to Address

#### Escalation System

Gastown's severity-based routing handles stuck agents gracefully. Erk currently lacks:

- Severity classification for issues
- Timeout-based re-escalation
- Routing rules by severity
- Acknowledgment protocol

**Potential adoption:**

- Add severity field to plan issues
- Implement stale detection in TUI
- Route critical issues to human attention
- Auto-escalate unacknowledged items

#### Background Monitoring

Gastown's Deacon provides continuous health oversight. Erk lacks:

- Periodic health sweeps
- Trend detection over time
- Automatic remediation triggers
- Cross-worktree visibility

**Potential adoption:**

- Background daemon watching worktrees
- Detect stuck implementations
- Identify resource leaks
- Report health summaries

#### Inter-Agent Messaging

Gastown's mail system enables agent coordination. Erk lacks:

- Formal message passing between agents
- Priority-based message handling
- Message acknowledgment protocol
- Cross-session communication

**Potential adoption:**

- Message beads/markers
- Priority levels for urgency
- Delivery confirmation
- Session-to-session relay

### Patterns Worth Adopting

#### Propulsion Principle

Fast startup when work is discovered. Applicable to:

- Plan implementations starting immediately
- CI fixes proceeding without confirmation
- Worktree setup completing autonomously

#### Stale Detection

Auto-escalate unacknowledged issues. Applicable to:

- Plan issues open too long
- PRs without review
- Stuck worktrees

#### Redundant Monitoring

Multiple observers for convergence. Applicable to:

- TUI + CLI + hooks all checking state
- Multiple verification points
- Self-healing through redundancy

#### Declarative Gates

Plugin conditions (cooldown, cron, manual). Applicable to:

- Plan step dependencies
- CI gate conditions
- Review requirements

### What Erk Does Well

Areas where Gastown could learn from Erk:

#### Planning Upfront in GitHub Issues

Erk's plan-first approach with GitHub issues provides:

- Human-readable plan artifacts
- Version control for plans
- Easy plan review and modification
- Integration with existing tooling

#### Fake-Driven Testing Architecture

Erk's 5-layer test architecture enables:

- Fast, deterministic tests
- Gateway abstraction for all external calls
- Comprehensive test coverage
- Easy mocking of complex scenarios

#### Worktree Isolation Model

Erk's worktree approach provides:

- Clean workspace per implementation
- Parallel work without conflicts
- Easy cleanup and reset
- Git-native isolation

## Appendix: Command Reference

Key `gt` commands mentioned in this document:

| Command       | Purpose                        |
| ------------- | ------------------------------ |
| `gt sling`    | Assign work to agent's hook    |
| `gt hook`     | View/manage hooked work        |
| `gt done`     | Complete work and release hook |
| `gt escalate` | Create/manage escalations      |
| `gt convoy`   | Manage batch work tracking     |
| `gt mail`     | Inter-agent messaging          |
| `gt molecule` | Manage workflow instances      |
| `bd close`    | Close bead (with `--continue`) |

## Appendix: Key File Locations

Gastown files referenced for deeper exploration:

| Path                    | Purpose                  |
| ----------------------- | ------------------------ |
| `.gastown/config.toml`  | Town-level configuration |
| `.gastown/mayor/`       | Mayor agent state        |
| `.gastown/deacon/`      | Deacon daemon state      |
| `rigs/<name>/.rig/`     | Rig configuration        |
| `rigs/<name>/refinery/` | Merge queue state        |
| `rigs/<name>/witness/`  | Health monitor state     |
| `rigs/<name>/polecats/` | Worker pool state        |
| `beads/*.jsonl`         | Ledger files             |
| `formulas/*.toml`       | Workflow templates       |

## Related Topics

- [Glossary](../glossary.md) - Erk-specific terminology
- [Erk Architecture](../architecture/erk-architecture.md) - Erk's architectural patterns
