# Beads as Alternative Backend for Objectives and Plans

This document analyzes [Beads](https://github.com/anthropics/beads) (`bd`) as a potential alternative backend for erk's objectives and plans system, comparing architectures, mapping concepts, and evaluating trade-offs.

## Executive Summary

Beads is a distributed, git-backed graph issue tracker optimized for AI agents. It offers several features that align well with erk's needs: hash-based IDs for conflict-free concurrent creation, dependency tracking, "ready work" discovery, and context window management through compaction. However, adopting beads would require significant architectural changes and would trade GitHub's collaboration features for local-first operation.

**Verdict**: Beads is a compelling option for teams prioritizing agent autonomy and offline operation, but the migration cost is substantial. A hybrid approach (beads for local planning, GitHub for PRs) may offer the best of both worlds.

---

## Current Erk System

### Storage Model

Erk stores objectives and plans as **GitHub Issues**:

| Entity    | Storage      | Label           | Content Location                     |
| --------- | ------------ | --------------- | ------------------------------------ |
| Objective | GitHub Issue | `erk-objective` | Issue body                           |
| Plan      | GitHub Issue | `erk-plan`      | Body=metadata, first comment=content |

### Data Model

**Plan fields** (stored in `plan-header` metadata block):

- `schema_version`, `created_at`, `created_by`
- `objective_issue` (parent linkage)
- `worktree_name`, `branch_name`
- Dispatch tracking: `last_dispatched_at`, `last_dispatched_run_id`
- Implementation tracking: `last_local_impl_at`, `last_remote_impl_at`
- Session tracking: `last_session_id`, `last_session_gist_url`

**Objective fields**: Minimal structure, content in body only.

### Linkage

```
Objective #123 (erk-objective)
├── Plan #456 (erk-plan, objective_issue=123)
│   └── Branch P456-feature → PR #789
└── Plan #457 (erk-plan, objective_issue=123)
    └── Branch P457-bugfix → PR #790
```

### Operations

- **Create**: `gh api` REST calls (avoiding GraphQL rate limits)
- **Query**: List issues by label, parse metadata blocks
- **Update**: Modify issue body or add comments
- **Link**: Store `objective_issue` in plan metadata

---

## Beads System

### Storage Model

Beads uses a **three-layer architecture**:

```
CLI Commands (bd create, list, ready, sync)
        ↓
SQLite Database (.beads/beads.db) — local cache, gitignored
        ↓
JSONL File (.beads/issues.jsonl) — git-tracked source of truth
        ↓
Remote Repository (git push/pull)
```

### Data Model

**Issue fields** (comprehensive):

```go
type Issue struct {
    // Identity
    ID              string      // Hash-based: bd-a1b2
    Title           string
    Description     string

    // Classification
    Status          Status      // open, in_progress, blocked, closed, tombstone, pinned, hooked
    Priority        int         // 0-4 (P0=critical)
    IssueType       IssueType   // bug, feature, task, epic, chore
    Labels          []string

    // Planning
    Design          string
    AcceptanceCriteria string
    Notes           string

    // Timestamps
    CreatedAt, UpdatedAt, ClosedAt time.Time
    DueAt, DeferUntil time.Time

    // Agent-specific
    HookBead        string      // Parent agent's active work
    RoleBead        string      // Role assignment
    AgentState      string      // Agent-managed JSON blob
    LastActivity    time.Time

    // Compaction (context management)
    CompactionLevel int
    CompactedAt     time.Time
    OriginalSize    int

    // Soft-delete
    DeletedAt       time.Time
    DeletedBy       string
    DeleteReason    string

    // Molecules (templates)
    MolType         string      // swarm, patrol, work
    IsTemplate      bool

    // Async coordination
    AwaitType       string      // gh:run, gh:pr, timer, human
    AwaitID         string
    Holder          string      // Exclusive slot holder
    Waiters         []string

    // Attribution (HOP)
    Creator         string
    Validations     []Validation
    QualityScore    float64
    Crystallizes    bool
}
```

**Dependency types**:

- `blocks`: Direct blocking (A blocks B)
- `related`: Loose association
- `parent-child`: Hierarchical (for epics)
- `discovered-from`: Audit trail
- `conditional-blocks`: Error-path dependencies

### Operations

- **Create**: `bd create "Title" --type feature --priority 1`
- **Query**: `bd list`, `bd ready` (shows unblocked work)
- **Update**: `bd update <id> --status in_progress`
- **Link**: `bd dep add <from> <to> --type parent-child`

---

## Feature Mapping

### Concept Alignment

| Erk Concept              | Beads Equivalent                  | Notes                                     |
| ------------------------ | --------------------------------- | ----------------------------------------- |
| Objective                | Epic (`--type epic`)              | Use `parent-child` deps for plan linkage  |
| Plan                     | Task/Feature issue                | `--type task` or `--type feature`         |
| `erk-plan` label         | `erk-plan` label                  | Beads supports arbitrary labels           |
| `erk-objective` label    | `erk-objective` label             | Plus `--type epic` for hierarchy          |
| `objective_issue` field  | `parent-child` dependency         | Native graph relationship                 |
| Plan state (OPEN/CLOSED) | `open`/`closed` status            | Plus `in_progress`, `blocked`, `deferred` |
| Metadata block           | Native fields + JSON `AgentState` | Richer structured data                    |
| GitHub issue number      | Hash-based ID (`bd-a1b2`)         | Conflict-free but different               |

### Workflow Mapping

**Current erk workflow**:

```
1. Create objective (GitHub issue)
2. Create plan linked to objective (GitHub issue with metadata)
3. Submit plan → creates branch + worktree
4. Implement → PR
5. Land PR → updates objective
```

**Beads workflow**:

```
1. bd create "Objective" --type epic
2. bd create "Plan" --type task
3. bd dep add <plan-id> <objective-id> --type parent-child
4. bd update <plan-id> --status in_progress
5. [Git operations unchanged]
6. bd update <plan-id> --status closed
7. bd ready --mol <objective-id>  # Shows remaining plans
```

### Ready Work Discovery

Beads provides `bd ready` which finds work that:

- Has status `open` or `in_progress`
- Has no open blocking dependencies
- Is not deferred past current time

This directly maps to erk's need to find "next plan to implement" for an objective.

---

## Advantages of Beads Backend

### 1. Conflict-Free Concurrent Creation

**Problem**: GitHub sequential issue numbers cause merge conflicts when agents create issues in parallel on different branches.

**Beads solution**: Hash-based IDs (e.g., `bd-a1b2`) from random UUIDs.

- Multiple agents can create plans simultaneously
- No coordination needed
- JSONL append-only format merges cleanly

### 2. Native Dependency Graph

**Problem**: Erk stores `objective_issue` as a metadata field, requiring parsing and filtering.

**Beads solution**: First-class `dependencies` table with typed relationships.

- Query: `bd list --blocked-by <objective-id>`
- Visualize: `bd tree <objective-id>`
- Multiple relationship types: `blocks`, `parent-child`, `conditional-blocks`

### 3. Ready Work Algorithm

**Problem**: Erk must iterate all plans and check metadata to find implementable work.

**Beads solution**: `bd ready` command with SQL-backed dependency resolution.

- Instant query: "What can I work on now?"
- Respects blocking relationships
- Supports deferred work (hidden until time passes)

### 4. Context Window Management

**Problem**: Long-lived objectives accumulate plans; loading all into agent context is wasteful.

**Beads solution**: Semantic compaction with "memory decay".

- Old closed plans summarized to single sentence
- `CompactionLevel` tracks how many times compacted
- `OriginalSize` preserved for analytics
- Agents see current context, not full history

### 5. Offline-First Operation

**Problem**: GitHub API rate limits affect agent workflows (especially GraphQL).

**Beads solution**: Local SQLite + git sync.

- All operations local (fast, no rate limits)
- Sync on git push/pull
- Works offline, syncs when connected

### 6. Agent Coordination Primitives

**Problem**: Erk lacks native support for agent waiting/coordination.

**Beads solution**: Gates and Slots.

- **Gates**: Wait for external conditions (`gh:run`, `gh:pr`, `timer`, `human`)
- **Slots**: Exclusive access (one agent at a time)
- **Waiters**: Notification when gate clears
- Query: `bd ready --gated` finds resumable work

### 7. Richer Status Model

**Problem**: Erk has binary OPEN/CLOSED state.

**Beads solution**: Granular statuses.

- `open`: Not started
- `in_progress`: Being worked
- `blocked`: Waiting on dependency
- `deferred`: Deliberately postponed (with `defer_until` time)
- `closed`: Complete
- `tombstone`: Soft-deleted (30-day TTL)
- `pinned`: Persistent context marker
- `hooked`: Attached to agent's active work

### 8. Deterministic Testing

**Problem**: Testing GitHub integration requires mocking or real API calls.

**Beads solution**: In-memory storage backend.

- Tests use memory backend (no SQLite, no git)
- Dual-mode test framework runs tests in both direct and daemon modes
- Fast unit tests, thorough integration tests

---

## Disadvantages and Gaps

### 1. Loss of GitHub Collaboration Features

**Erk's GitHub benefits**:

- Web UI for viewing/editing issues
- Notification system (mentions, assignments)
- Cross-linking with PRs (`Closes #123`)
- Search across organization
- Access control (org permissions)
- Mobile app access

**Beads gap**: No web UI, no notifications, no cross-repo visibility without explicit federation.

### 2. Different ID Scheme

**Current**: GitHub issue numbers (`#123`) are familiar, sequential, linkable.

**Beads**: Hash IDs (`bd-a1b2`) are unfamiliar, harder to remember, no direct URL.

**Migration pain**: Existing issues can't be imported with same IDs.

### 3. PR Integration Loss

**Current**: GitHub auto-closes issues when PR merges with `Closes #123`.

**Beads**: Requires explicit `bd update <id> --status closed` after merge.

**Workaround**: Git hook or CI action to close beads issues on PR merge.

### 4. No Native Cross-Repo Support

**Current**: Plans can reference external repos via `source_repo` metadata.

**Beads**: Single `.beads/` per repo. Federation possible but not built-in.

### 5. Additional Tooling Requirement

**Current**: Only needs `gh` CLI (installed on most dev machines).

**Beads**: Requires installing `bd` CLI, learning new commands.

### 6. Sync Complexity

**Current**: GitHub is always consistent (server is source of truth).

**Beads**: Must handle sync conflicts, stale database detection, import/export timing.

### 7. No Web Search/Discovery

**Current**: Can find issues via GitHub search, linked from anywhere.

**Beads**: Issues only visible to those with repo access and `bd` installed.

---

## Migration Considerations

### Data Migration

Erk plans store:

```yaml
schema_version: "2"
created_at: 2025-01-15T10:30:00Z
created_by: username
objective_issue: 123
worktree_name: P456-feature
branch_name: P456-feature-01-15-1430
```

Beads equivalent:

```bash
bd create "Plan title" \
  --type task \
  --label erk-plan \
  --meta '{"schema_version":"2","worktree_name":"P456-feature","branch_name":"..."}'
bd dep add <new-plan-id> <objective-id> --type parent-child
```

### Gateway Abstraction

Erk already has `PlanBackend` interface:

```python
class PlanBackend(Protocol):
    def get_plan(self, repo_root: Path, plan_id: str) -> Plan: ...
    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]: ...
    def create_plan(self, ...) -> CreatePlanResult: ...
    def update_metadata(self, repo_root: Path, plan_id: str, metadata: dict) -> None: ...
    def close_plan(self, repo_root: Path, plan_id: str) -> None: ...
```

A `BeadsPlanBackend` implementation could wrap `bd` CLI calls:

```python
class BeadsPlanBackend:
    def create_plan(self, ...) -> CreatePlanResult:
        result = subprocess.run(["bd", "create", title, "--json", ...])
        return CreatePlanResult(plan_id=result["id"], url=None)

    def list_plans(self, repo_root: Path, query: PlanQuery) -> list[Plan]:
        result = subprocess.run(["bd", "list", "--label", "erk-plan", "--json"])
        return [self._to_plan(issue) for issue in result]
```

### Hybrid Approach

Keep GitHub for some functions, use beads for others:

| Function          | Backend | Rationale                                |
| ----------------- | ------- | ---------------------------------------- |
| PRs               | GitHub  | Native integration, reviews, CI          |
| Objectives        | GitHub  | Web visibility, notifications            |
| Plans             | Beads   | Local-first, conflict-free, dependencies |
| Progress tracking | Beads   | `bd update --status`, gates              |

Sync mechanism:

- On plan creation: Create beads issue, store beads ID in GitHub issue metadata
- On PR merge: Git hook closes beads issue
- On objective query: Fetch linked beads issues via stored IDs

---

## Architectural Comparison

### Current (GitHub-Native)

```
                    ┌─────────────────────────────────────┐
                    │           GitHub API                │
                    │  ┌─────────┐      ┌─────────┐       │
                    │  │ Issues  │      │   PRs   │       │
                    │  └────┬────┘      └────┬────┘       │
                    │       │ Closes #N      │            │
                    │       └────────────────┘            │
                    └───────────────┬─────────────────────┘
                                    │ REST API
                    ┌───────────────┴─────────────────────┐
                    │           erk CLI                   │
                    │  ┌─────────────────────────────┐    │
                    │  │   GitHubPlanStore           │    │
                    │  │   (PlanBackend impl)        │    │
                    │  └─────────────────────────────┘    │
                    └─────────────────────────────────────┘
```

### Proposed (Beads Backend)

```
┌─────────────────────────────────────┐
│           GitHub API                │
│  ┌─────────────────────────────┐    │
│  │   PRs (unchanged)           │    │
│  └─────────────────────────────┘    │
└───────────────┬─────────────────────┘
                │ PR operations only
┌───────────────┴─────────────────────┐      ┌──────────────────────────┐
│           erk CLI                   │      │   .beads/                │
│  ┌─────────────────────────────┐    │      │  ├── beads.db (cache)    │
│  │   BeadsPlanBackend          │◄───┼──────┤  └── issues.jsonl (git)  │
│  │   (PlanBackend impl)        │    │      │                          │
│  └─────────────────────────────┘    │      │  Syncs via git push/pull │
└─────────────────────────────────────┘      └──────────────────────────┘
```

### Hybrid (Best of Both)

```
┌─────────────────────────────────────┐
│           GitHub API                │
│  ┌─────────────┐  ┌─────────────┐   │
│  │ Objectives  │  │    PRs      │   │
│  │ (visibility)│  │ (reviews)   │   │
│  └──────┬──────┘  └─────────────┘   │
└─────────┼───────────────────────────┘
          │ beads_id in metadata
┌─────────┼───────────────────────────┐      ┌──────────────────────────┐
│         │     erk CLI               │      │   .beads/                │
│  ┌──────┴──────────────────────┐    │      │  Plans + dependencies    │
│  │   HybridPlanBackend         │◄───┼──────┤  Ready work queries      │
│  │   GitHub objectives         │    │      │  Compaction              │
│  │   Beads plans               │    │      │  Agent coordination      │
│  └─────────────────────────────┘    │      └──────────────────────────┘
└─────────────────────────────────────┘
```

---

## Implementation Effort Estimate

### Full Migration

| Component                | Scope                                           |
| ------------------------ | ----------------------------------------------- |
| `BeadsPlanBackend` class | New implementation of `PlanBackend` protocol    |
| Plan ID migration        | Update all code expecting `int` issue numbers   |
| CLI commands             | Update `erk plan`, `erk objective` to use beads |
| Dependency tracking      | Replace metadata parsing with `bd dep` queries  |
| Ready work               | Replace custom logic with `bd ready`            |
| Tests                    | New fake for beads backend                      |
| Documentation            | Update all planning docs                        |

### Hybrid Approach

| Component                | Scope                                           |
| ------------------------ | ----------------------------------------------- |
| `BeadsPlanBackend` class | Partial implementation for plans only           |
| Objective linkage        | Store beads ID in GitHub issue metadata         |
| Sync hooks               | Git hooks to close beads issues on PR merge     |
| Migration script         | Optional: import existing GitHub plans to beads |

---

## Recommendation

### When to Choose Beads

- **Multi-agent workflows** where agents create plans concurrently
- **Offline-first environments** with intermittent connectivity
- **Long-horizon projects** where context window management matters
- **Complex dependency graphs** beyond simple parent-child
- **Agent coordination** needs (gates, slots, async waiting)

### When to Keep GitHub

- **Team collaboration** with non-agent contributors
- **Organization visibility** (search, notifications, mobile)
- **PR integration** (auto-close, cross-references)
- **Existing tooling** (GitHub Actions, project boards)

### Suggested Path Forward

1. **Phase 1**: Implement `BeadsPlanBackend` as optional backend (config toggle)
2. **Phase 2**: Use beads for local agent planning (single-agent, single-machine)
3. **Phase 3**: Evaluate hybrid approach for multi-agent scenarios
4. **Phase 4**: Consider full migration if GitHub pain points become blockers

---

## Appendix: Beads CLI Reference

Common commands relevant to erk workflows:

```bash
# Create objective (epic)
bd create "Implement auth system" --type epic --label erk-objective

# Create plan linked to objective
bd create "Add login endpoint" --type task --label erk-plan
bd dep add <plan-id> <objective-id> --type parent-child

# Find ready work for objective
bd ready --label erk-plan --blocked-by <objective-id>

# Update plan status
bd update <plan-id> --status in_progress
bd update <plan-id> --status closed

# View dependency tree
bd tree <objective-id>

# Compact old closed issues
bd compact --older-than 30d

# Sync with remote
bd sync
```

## Appendix: Key Beads Concepts

### Hash-Based IDs

Generated from random UUIDs, starting at 4 characters and growing as needed:

- `bd-a1b2` (initial)
- `bd-a1b2c` (after collisions)

### Content-Hash Deduplication

SHA256 of substantive fields determines import behavior:

- Same ID + different hash → UPDATE
- Same ID + same hash → SKIP

### Debounced Export

5-second batching prevents excessive commits:

1. First write marks dirty, starts timer
2. Subsequent writes accumulate
3. After 5s, single export flushes all changes

### Soft-Delete (Tombstones)

Deleted issues get `tombstone` status with 30-day TTL:

- Preserves audit trail
- Eventually purged in compaction
- `--hard` flag for immediate deletion
