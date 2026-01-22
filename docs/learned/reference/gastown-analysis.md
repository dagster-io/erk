---
title: Gastown Architecture Analysis
read_when:
  - "understanding multi-agent coordination patterns"
  - "designing escalation or inter-agent messaging systems"
  - "exploring propulsion-based agent architectures"
  - "comparing erk to other agentic systems"
---

# Gastown Architecture Analysis

> **Version Warning:** This document captures Gastown at commit `b158ff27c25efa02ad2a6948a923186a99c6a429` (v0.5.0, 2026-01-21). Gastown is rapidly evolving—consult the [Gastown repository](https://github.com/gastown/gastown) for the current state.

## Executive Summary

Gastown is a multi-project agentic engineering system built around the "steam engine" metaphor—agents act as pistons that activate when work appears on their hook, creating mechanical propulsion rather than polling or coordination. It uses a git-backed ledger system called "beads" for state tracking and employs a hierarchy of specialized agents (Mayor, Deacon, Witness, Refinery, Polecats) to coordinate work across multiple projects ("rigs") within a "town."

This document exists to capture Gastown's architectural insights for cross-pollination with Erk, particularly around patterns Erk hasn't yet implemented (escalation, inter-agent messaging, background daemons).

## Core Philosophy

### The Steam Engine Metaphor

Gastown treats agent coordination like a steam engine:

- **Agents are pistons** — They activate on pressure (work appearing), not schedules
- **Work creates pressure** — Issues, PRs, and state changes push agents into motion
- **Propulsion, not polling** — Agents don't ask "is there work?" — work finds them

### The Propulsion Principle

> "If you find work on your hook, YOU RUN IT."

This is Gastown's central operating principle. When an agent wakes up:

1. Check your hook for pinned work
2. If work exists, execute it immediately
3. Don't announce, don't delegate, don't defer — just run

Anti-patterns this prevents:

- **Polling loops** — No "check every N seconds" patterns
- **Announcement overhead** — No "I'm going to do X" before doing X
- **Coordination bottlenecks** — No central dispatcher required

### Physics Over Politeness

Gastown prefers mechanical guarantees over social conventions:

- State changes trigger actions deterministically
- Agents don't negotiate or coordinate — they respond to state
- The system converges through physics (hooks, state), not protocols

### Attribution as First-Class Concern

Every action in Gastown tracks its actor:

- `BD_ACTOR` environment variable identifies the acting agent
- Commits carry attribution metadata
- Audit trails enable debugging and accountability

## Architecture Overview

### Town Structure

```
town/
├── .bd/                    # Town-level beads (ledger)
│   ├── beads/              # JSONL bead files
│   └── config.toml         # Town configuration
├── mayor/                  # Town coordinator agent
├── deacon/                 # Background daemon
├── rigs/                   # Project containers
│   ├── project-a/
│   │   ├── .bd/            # Rig-level beads
│   │   ├── witness/        # Health monitor
│   │   ├── refinery/       # Merge queue processor
│   │   ├── polecats/       # Worker agents
│   │   └── [project files]
│   └── project-b/
│       └── ...
└── boot/                   # Ephemeral triage agent
```

### Two-Level Beads Architecture

Gastown maintains beads (state) at two levels:

1. **Town-level beads** (`town/.bd/`) — Cross-rig concerns, escalations, convoys
2. **Rig-level beads** (`rig/.bd/`) — Per-project issues, PRs, work items

This separation enables:

- Rig isolation (projects don't interfere)
- Town-wide coordination (cross-project work tracking)
- Different retention policies per level

### Component Hierarchy

```
                    ┌─────────┐
                    │  Mayor  │  Town-level coordinator
                    └────┬────┘
                         │
              ┌──────────┼──────────┐
              │          │          │
         ┌────┴────┐ ┌───┴────┐ ┌───┴───┐
         │ Deacon  │ │  Boot  │ │ [Rig] │
         └─────────┘ └────────┘ └───┬───┘
              Background   Ephemeral    │
              daemon       triage       │
                              ┌─────────┼─────────┐
                              │         │         │
                         ┌────┴───┐ ┌───┴────┐ ┌──┴──────┐
                         │Witness │ │Refinery│ │Polecats │
                         └────────┘ └────────┘ └─────────┘
                         Health     Merge      Worker
                         monitor    queue      agents
```

## Core Abstractions

### Town

A **town** is Gastown's top-level container—a directory structure housing multiple projects (rigs) with shared infrastructure.

**Key characteristics:**

- Single town per deployment
- Houses town-level beads for cross-rig concerns
- Contains shared agents (Mayor, Deacon, Boot)

**Directory structure:**

| Path      | Purpose                     |
| --------- | --------------------------- |
| `.bd/`    | Town-level beads ledger     |
| `mayor/`  | Town coordinator workspace  |
| `deacon/` | Background daemon workspace |
| `boot/`   | Ephemeral triage workspace  |
| `rigs/`   | Project containers          |

**Configuration** (`config.toml`):

- Rig definitions and paths
- Escalation routing rules
- Daemon intervals

### Rigs

A **rig** is a project container within a town—an isolated workspace for a single codebase with its own agents and state.

**Key characteristics:**

- One rig per project/repository
- Has its own beads ledger (rig-level state)
- Contains per-rig agents (Witness, Refinery, Polecats)

**Rig components:**

| Component   | Purpose                           |
| ----------- | --------------------------------- |
| `.bd/`      | Rig-level beads                   |
| `witness/`  | Health monitoring agent workspace |
| `refinery/` | Merge queue processor workspace   |
| `polecats/` | Worker agent workspaces           |
| `crew/`     | Agent configurations              |

### Agents

Gastown uses specialized agents with distinct responsibilities:

#### Mayor

The town-level coordinator. Responsibilities:

- Planning and prioritization across rigs
- Spawning work for other agents
- Cross-rig coordination

#### Deacon

The background daemon. Responsibilities:

- Periodic patrol cycles (health checks)
- Stale work detection
- Escalation monitoring
- Runs on a schedule, not on-demand

#### Boot

The ephemeral triage agent. Characteristics:

- Fresh context on every tick (no memory between runs)
- Handles incoming work classification
- Routes work to appropriate agents

#### Witness

Per-rig health monitor. Responsibilities:

- Monitors rig health metrics
- Detects stuck PRs, stale branches
- Creates escalations when issues detected

#### Refinery

Per-rig merge queue processor. Responsibilities:

- Manages the merge queue
- Handles PR sequencing
- Coordinates with CI systems

#### Polecats

Ephemeral worker agents. Characteristics:

- Spawned for specific tasks
- Self-terminate on completion (`gt done`)
- Multiple can run in parallel

### Beads (Ledger System)

**Beads** are Gastown's state tracking mechanism—a git-backed JSONL ledger system.

**What beads are:**

- JSONL files in `.bd/beads/`
- Each line is a discrete state entry
- Git-backed for history and durability

**Bead anatomy:**

```json
{
  "id": "bead-123",
  "type": "issue",
  "status": "open",
  "labels": ["bug", "p1"],
  "description": "Something is broken",
  "created_at": "2026-01-21T10:00:00Z",
  "actor": "polecat-7"
}
```

**Key fields:**

| Field         | Purpose                    |
| ------------- | -------------------------- |
| `id`          | Unique identifier          |
| `type`        | Bead type (issue, pr, etc) |
| `status`      | Current state              |
| `labels`      | Classification tags        |
| `description` | Human-readable summary     |
| `actor`       | Who created/modified       |

#### Wisps

**Wisps** are ephemeral bead entries—high-frequency state changes that get squashed into digests periodically.

Purpose:

- Capture fine-grained state (progress updates, heartbeats)
- Avoid ledger bloat from frequent writes
- Digest creation consolidates wisps

### Hooks

**Hooks** are Gastown's work assignment mechanism—how work gets pinned to agents.

**Hook lifecycle:**

1. **Pin** — Work gets pinned to an agent's hook
2. **Execute** — Agent wakes, finds work, runs it (propulsion principle)
3. **Done** — Agent completes, unpins work, may self-terminate

**Relation to propulsion principle:**

Hooks ARE the pressure in the steam engine metaphor. When work appears on a hook, it creates pressure that activates the agent.

**Key commands:**

- `gt sling <work> --to <agent>` — Pin work to agent's hook
- `gt hook` — View what's on your hook
- `gt done` — Complete hooked work, self-clean

### Molecules & Formulas

Gastown uses a workflow templating system:

#### Formulas

**Formulas** are TOML workflow templates—reusable multi-step procedures.

```toml
[formula]
name = "fix-and-ship"
steps = ["diagnose", "implement", "test", "pr"]

[steps.diagnose]
type = "investigate"
next = "implement"

[steps.implement]
type = "code"
next = "test"
```

#### Protomolecules

**Protomolecules** are frozen, ready-to-instantiate formulas—templates that have been validated and prepared for use.

#### Molecules

**Molecules** are active instances of formulas—running workflows with step beads tracking progress.

**Step transitions:**

Agents advance through molecule steps with:

```bash
bd close --continue  # Complete current step, advance to next
```

### Convoys

**Convoys** track batch work—multiple related issues/PRs that form a logical unit.

**Key characteristics:**

- Group tracking for related work items
- Auto-completion when all items finish
- Swarm concept: active workers on convoy issues

**Example:** A "refactor auth" convoy might track:

- Issue: Update auth middleware
- Issue: Migrate user sessions
- Issue: Update tests
- PR: Combined auth refactor

When all tracked items close, the convoy auto-completes.

### Mail System

**Mail** provides inter-agent messaging—formal communication between agents.

**Characteristics:**

- Priority levels (urgent, normal, low)
- Inbox/outbox model per agent
- Persistent (survives agent restarts)

**Key commands:**

- `gt mail send --to <agent> --priority <level> "message"`
- `gt mail inbox` — Check incoming messages
- `gt mail outbox` — Check sent messages

### Escalation System

**Escalations** handle severity-based routing when agents get stuck.

**Severity levels:**

| Level    | Meaning                        | Response time |
| -------- | ------------------------------ | ------------- |
| critical | System down, data loss risk    | Immediate     |
| high     | Major feature broken           | Hours         |
| medium   | Degraded functionality         | Day           |
| low      | Minor issue, workaround exists | Week          |

**Escalation lifecycle:**

1. **Create** — Agent or system creates escalation
2. **Route** — System routes to configured responders
3. **Acknowledge** — Responder acks receipt
4. **Stale detection** — Unacked escalations auto-reescalate
5. **Close** — Issue resolved, escalation closed

**Key commands:**

- `gt escalate --severity <level> "description"`
- `gt escalate ack <id>` — Acknowledge escalation
- `gt escalate close <id>` — Close resolved escalation

## Key Design Patterns

### Propulsion Principle (Detailed)

The propulsion principle is Gastown's core behavioral pattern.

**The rule:**

> When you wake up and find work on your hook, YOU RUN IT. Don't announce, don't ask permission, don't coordinate — execute.

**Why it works:**

- **Eliminates coordination overhead** — No need for central scheduler
- **Minimizes latency** — Work starts immediately when agent wakes
- **Self-healing** — If an agent fails, work remains hooked until another agent picks it up

**Implementation:**

```
agent_wakeup():
    work = check_hook()
    if work:
        execute(work)      # Propulsion: just run it
        mark_done(work)
    else:
        idle_or_terminate()
```

**Anti-patterns:**

| Pattern          | Problem                           | Propulsion fix     |
| ---------------- | --------------------------------- | ------------------ |
| Polling          | "Is there work?" wastes cycles    | Work finds you     |
| Announcement     | "I'm going to..." adds latency    | Just do it         |
| Coordination     | "Let me check with..." bottleneck | Independent action |
| Central dispatch | Single point of failure           | Distributed hooks  |

### Event-Driven Completion

Gastown uses event-driven patterns for detecting work completion.

**How convoys detect completion:**

1. Convoy tracks set of beads (issues, PRs)
2. Each bead close triggers state check
3. When all beads closed, convoy auto-completes

**Redundant monitoring:**

Multiple observers watch for completion:

- **Deacon** — Periodic patrol catches missed events
- **Witness** — Per-rig monitoring
- **Refinery** — Merge queue events

This redundancy ensures convergence even if one monitor fails.

### Separation of Transport/Triage/Execution

Gastown separates concerns across agent types:

| Layer     | Agent  | Language | Characteristics         |
| --------- | ------ | -------- | ----------------------- |
| Transport | Daemon | Go       | Mechanical heartbeat    |
| Triage    | Boot   | AI       | Fresh context, classify |
| Execution | Others | AI       | Long-running, stateful  |

**Why separate:**

- Daemon (Go) is reliable, fast, deterministic
- Boot (ephemeral AI) has no stale context to corrupt decisions
- Execution agents (AI) benefit from accumulated context

### Reality-First State

Gastown queries observables rather than trusting metadata.

**Principle:** Git state is truth; metadata is cache.

**Examples:**

- Don't trust "PR merged" metadata — check `git branch --merged`
- Don't trust "issue closed" flag — query actual state
- Beads are records of observations, not the observations themselves

### Attribution & Provenance

Every action carries attribution:

**BD_ACTOR environment variable:**

All Gastown commands check `BD_ACTOR` to identify the acting agent.

```bash
export BD_ACTOR="polecat-7"
gt commit -m "Fix bug"  # Commit attributed to polecat-7
```

**Commit attribution:**

Commits include trailers identifying the responsible agent.

**Audit trails:**

Beads record who created/modified them, enabling post-hoc debugging.

## Concept Mapping: Gastown → Erk

| Gastown Concept | Erk Equivalent     | Notes                                    |
| --------------- | ------------------ | ---------------------------------------- |
| Town            | (no equivalent)    | Erk is single-workspace focused          |
| Rig             | Worktree           | Both provide isolated work environments  |
| Polecat         | Agent in worktree  | Both are ephemeral workers               |
| Mayor           | Planning phase     | Both coordinate and plan work            |
| Convoy          | Objective          | Both track multi-PR work units           |
| Beads           | Markers + sessions | Both persist agent state                 |
| Molecules       | Plan steps         | Both structure multi-step workflows      |
| Wisps           | (no equivalent)    | Erk lacks ephemeral high-frequency state |
| Formulas        | (no equivalent)    | Erk lacks workflow templates             |
| Hook            | Markers (partial)  | Both assign work, different mechanics    |
| Escalation      | **(missing)**      | **Critical gap in Erk**                  |
| Mail            | **(missing)**      | **Critical gap in Erk**                  |
| Deacon          | **(missing)**      | **Critical gap in Erk**                  |
| Witness         | **(missing)**      | Erk lacks per-worktree health monitoring |
| Refinery        | **(missing)**      | Erk lacks automated merge queue          |
| Boot            | **(missing)**      | Erk lacks ephemeral triage agent         |

**Key observations:**

- Erk has comparable isolation (worktrees) and planning (GitHub issues)
- Erk lacks Gastown's operational infrastructure (daemons, escalation, messaging)
- Gastown's multi-project (town/rig) model is more complex than Erk needs

## Learnings for Erk

### Critical Gaps to Address

#### Escalation System

Erk lacks severity-based routing when agents get stuck.

**What Gastown has:**

- Severity levels (critical/high/medium/low)
- Routing configuration per severity
- Auto-reescalation on stale acknowledgments

**What Erk should consider:**

- Define severity levels appropriate for Erk's use cases
- Add escalation routing (to human, to different agent, etc.)
- Implement stale detection with auto-reescalation

#### Background Monitoring

Erk lacks a daemon for health checks.

**What Gastown has:**

- Deacon daemon runs periodic patrols
- Detects stuck work, stale state
- Triggers escalations proactively

**What Erk should consider:**

- Periodic worktree health checks
- Stuck PR detection
- Stale plan detection

#### Inter-Agent Messaging

Erk lacks formal agent-to-agent communication.

**What Gastown has:**

- Priority-based messaging
- Persistent inbox/outbox
- Delivery confirmation

**What Erk should consider:**

- How should parallel agents communicate?
- Should messages persist across sessions?
- Priority levels for different message types

### Patterns Worth Adopting

#### Propulsion Principle

Fast startup behavior—agents that find work immediately execute it.

**Erk application:**

- Plan-implement could apply propulsion (find plan → execute immediately)
- Avoid "announcing" phases that add latency
- Consider: does Erk over-coordinate?

#### Stale Detection

Auto-escalate unacknowledged issues.

**Erk application:**

- Detect stale plans (created but not implemented)
- Detect stale PRs (open too long without activity)
- Detect stale worktrees (no commits for extended period)

#### Redundant Monitoring

Multiple observers ensure convergence.

**Erk application:**

- Don't rely on single point of status tracking
- Consider: what happens if a session crashes mid-plan?
- Redundant state in GitHub issue + local markers

#### Declarative Gates

Plugin conditions for workflow control.

**Erk application:**

- Cooldown gates (don't run too frequently)
- Cron gates (schedule-based execution)
- Manual gates (require human approval)

### What Erk Does Well

These are areas where Gastown could learn from Erk:

#### Planning Upfront in GitHub Issues

Erk's plan-first workflow with GitHub issue persistence is more explicit than Gastown's formula system.

#### Fake-Driven Testing Architecture

Erk's 5-layer testing architecture with comprehensive fakes enables thorough testing of agent workflows—Gastown could benefit from similar patterns.

#### Worktree Isolation Model

Erk's worktree-based isolation is simpler than Gastown's rig model while achieving similar benefits.

## Appendix: Command Reference

Key `gt` commands mentioned in this document:

| Command                                   | Purpose                   |
| ----------------------------------------- | ------------------------- |
| `gt sling <work> --to <agent>`            | Pin work to agent's hook  |
| `gt hook`                                 | View hooked work          |
| `gt done`                                 | Complete work, self-clean |
| `gt escalate [--severity <level>] "desc"` | Create escalation         |
| `gt escalate ack <id>`                    | Acknowledge escalation    |
| `gt escalate close <id>`                  | Close escalation          |
| `gt convoy create <name>`                 | Create work batch         |
| `gt convoy track <id> <bead>`             | Add bead to convoy        |
| `gt mail send --to <agent> "msg"`         | Send inter-agent message  |
| `gt mail inbox`                           | Check incoming messages   |
| `bd close --continue`                     | Advance molecule step     |

## Appendix: Key File Locations

Key Gastown files for deeper exploration:

| Path                   | Content                          |
| ---------------------- | -------------------------------- |
| `cmd/gt/`              | CLI command implementations      |
| `internal/town/`       | Town management logic            |
| `internal/rig/`        | Rig management logic             |
| `internal/bead/`       | Bead/ledger system               |
| `internal/hook/`       | Hook mechanism                   |
| `internal/molecule/`   | Workflow templating              |
| `internal/escalation/` | Escalation system                |
| `internal/mail/`       | Inter-agent messaging            |
| `internal/deacon/`     | Background daemon                |
| `docs/philosophy.md`   | Propulsion principle explanation |
| `docs/steam-engine.md` | Metaphor documentation           |

## Related Topics

- [Erk Glossary](../glossary.md) - Erk-specific terminology
- [Planning Lifecycle](../planning/lifecycle.md) - Erk's plan-first workflow
- [Worktree Management](../erk/) - Erk's isolation model
