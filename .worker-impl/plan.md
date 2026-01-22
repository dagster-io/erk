# Plan: Create Exhaustive Gastown Learned Document

## Objective

Create a comprehensive `docs/learned/reference/gastown-analysis.md` document that captures Gastown's architecture, abstractions, and learnings for Erk—serving as a point-in-time reference for a rapidly evolving system.

## Metadata

- **Gastown commit:** `b158ff27c25efa02ad2a6948a923186a99c6a429`
- **Gastown version:** v0.5.0
- **Gastown date:** 2026-01-21
- **Document location:** `docs/learned/reference/gastown-analysis.md`

## Document Structure

### 1. Header & Versioning
- Title, date captured, commit hash, explicit warning about rapid evolution
- Link to Gastown repo for current state

### 2. Executive Summary
- One-paragraph "what is Gastown"
- Why this document exists (cross-pollination, learning from parallel approaches)

### 3. Core Philosophy
- Steam engine metaphor (agents as pistons)
- Propulsion principle ("if you find work on your hook, YOU RUN IT")
- Physics over politeness
- Attribution as first-class concern

### 4. Architecture Overview
- Town structure diagram (ASCII)
- Two-level beads architecture (town-level vs rig-level)
- Component hierarchy (Mayor → Deacon → Witness/Refinery → Polecats)

### 5. Core Abstractions (Detailed)

#### 5.1 Town
- What it is, directory structure
- Configuration files and their purposes

#### 5.2 Rigs
- Project containers
- Rig components (mayor/, refinery/, witness/, crew/, polecats/)
- Rig-level beads

#### 5.3 Agents
- **Mayor:** Town-level coordinator
- **Deacon:** Background daemon, patrol cycles
- **Boot:** Ephemeral triage agent (fresh context each tick)
- **Witness:** Per-rig health monitor
- **Refinery:** Per-rig merge queue processor
- **Polecats:** Ephemeral worker agents

#### 5.4 Beads (Ledger System)
- What beads are (git-backed JSONL issues)
- Bead anatomy (id, type, status, labels, description)
- Wisps (ephemeral entries, squashed to digests)
- Cross-rig references

#### 5.5 Hooks
- Work assignment mechanism
- Hook lifecycle (pin → execute → done)
- Relation to propulsion principle

#### 5.6 Molecules & Formulas
- Formulas (TOML workflow templates)
- Protomolecules (frozen, ready to instantiate)
- Molecules (active instances with step beads)
- Step transitions (`bd close --continue`)

#### 5.7 Convoys
- Batch work tracking
- Swarm concept (active workers on convoy issues)
- Auto-completion when all tracked items finish

#### 5.8 Mail System
- Inter-agent messaging
- Priority levels
- Inbox/outbox model

#### 5.9 Escalation System
- Severity levels (critical/high/medium/low)
- Routing configuration
- Stale detection and auto-reescalation
- Acknowledgment and closure

### 6. Key Design Patterns

#### 6.1 Propulsion Principle
- Full explanation with examples
- Anti-patterns (polling, announcement)

#### 6.2 Event-Driven Completion
- How convoys detect completion
- Redundant monitoring (Deacon + Witness + Refinery)

#### 6.3 Separation of Transport/Triage/Execution
- Daemon (Go, mechanical heartbeat)
- Boot (ephemeral AI, fresh context)
- Deacon (long-running agent)

#### 6.4 Reality-First State
- Query observables, not metadata
- Git as source of truth

#### 6.5 Attribution & Provenance
- BD_ACTOR environment variable
- Commit attribution
- Audit trails

### 7. Concept Mapping: Gastown → Erk

| Gastown | Erk | Notes |
|---------|-----|-------|
| Town | (no equivalent) | Erk is single-workspace |
| Rig | Worktree | Both isolate work |
| Polecat | Agent in worktree | Both ephemeral workers |
| Mayor | Planning phase | Both coordinate |
| Convoy | Objective | Both track multi-PR work |
| Beads | Markers + sessions | Both persist state |
| Molecules | Plan steps | Both structure workflows |
| Hook | (partial: markers) | Assignment mechanism |
| Escalation | (missing) | Critical gap |
| Mail | (missing) | Inter-agent messaging |
| Deacon | (missing) | Background daemon |

### 8. Learnings for Erk

#### 8.1 Critical Gaps to Address
- **Escalation system** - Severity-based routing when agents stuck
- **Background monitoring** - Daemon for health checks
- **Inter-agent messaging** - Formal communication protocol

#### 8.2 Patterns Worth Adopting
- **Propulsion principle** - Fast startup behavior
- **Stale detection** - Auto-escalate unacknowledged issues
- **Redundant monitoring** - Multiple observers for convergence
- **Declarative gates** - Plugin conditions (cooldown, cron, manual)

#### 8.3 What Erk Does Well (Gastown could learn)
- Planning upfront in GitHub issues
- Fake-driven testing architecture
- Worktree isolation model

### 9. Appendix: Command Reference

Brief reference of key `gt` commands mentioned:
- `gt sling` - Assign work to agent
- `gt hook` - View/manage hooked work
- `gt done` - Complete work and self-clean
- `gt escalate` - Create/manage escalations
- `gt convoy` - Manage work batches
- `gt mail` - Inter-agent messaging

### 10. Appendix: File Locations

Key Gastown files referenced in this document for deeper exploration.

---

## Implementation Steps

### Step 1: Create document skeleton
- Create `docs/learned/reference/gastown-analysis.md`
- Add frontmatter (category: reference, read-when conditions)
- Add header with versioning warning

### Step 2: Write sections 1-4 (Overview)
- Executive summary
- Core philosophy
- Architecture overview with ASCII diagram

### Step 3: Write section 5 (Core Abstractions)
- Each abstraction with clear definition
- How it works mechanically
- Key commands/files

### Step 4: Write section 6 (Design Patterns)
- Propulsion principle (detailed)
- Event-driven completion
- Other patterns

### Step 5: Write section 7 (Concept Mapping)
- Comprehensive mapping table
- Notes on similarities/differences

### Step 6: Write section 8 (Learnings)
- Critical gaps
- Patterns to adopt
- Erk strengths

### Step 7: Write appendices
- Command reference
- File locations

### Step 8: Update index
- Add entry to `docs/learned/index.md`
- Add to routing table if needed

### Step 9: Format and verify
- Run prettier on the markdown
- Verify links and structure

---

## Files to Modify

1. **Create:** `docs/learned/reference/gastown-analysis.md` (new document)
2. **Edit:** `docs/learned/index.md` (add entry)

## Verification

- Document renders correctly in markdown preview
- All sections are complete and detailed
- Concept mapping is accurate
- Frontmatter follows learned-docs conventions
- Entry added to index with appropriate "read when" condition

## Related Documentation

- `learned-docs` skill for document structure conventions
- `docs/learned/index.md` for index format