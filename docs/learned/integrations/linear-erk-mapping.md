---
title: Erk to Linear Concept Mapping
description: How erk concepts map to Linear's ontology
read_when:
  - Evaluating Linear as issue tracker for erk
  - Building Linear gateway
  - Understanding trade-offs between GitHub Issues and Linear
---

# Erk to Linear Concept Mapping

This document maps erk's current concepts to Linear's ontology, highlighting where Linear provides better primitives and where concepts don't map.

## Key Insight: AgentSession > Metadata Blocks

Linear's `AgentSession` is a **better fit** than erk's current GitHub metadata blocks for implementation tracking.

### Current Erk Approach

Erk embeds YAML in GitHub issue bodies:

```yaml
<!-- erk:metadata-block:plan-header -->
schema_version: "2"
created_at: "2025-01-03T12:00:00Z"
last_local_impl_at: "2025-01-03T14:00:00Z"
last_local_impl_event: "started"
last_local_impl_session: "abc-123-def"
last_local_impl_user: "schrockn"
```

Problems:

- No UI support (just raw YAML in collapsible)
- Manual parsing required
- No real-time updates
- No structured activity tracking

### Linear AgentSession Equivalent

| Erk Metadata Field                      | Linear AgentSession                |
| --------------------------------------- | ---------------------------------- |
| `last_local_impl_at`                    | `startedAt`                        |
| `last_local_impl_event` (started/ended) | `status` (pending/active/complete) |
| `last_local_impl_session`               | `id`                               |
| `last_local_impl_user`                  | `creator`                          |
| (no equivalent)                         | `activities` - structured progress |
| (no equivalent)                         | `summary` - completion summary     |
| (no equivalent)                         | `externalUrls` - PR links          |

### Why Linear is Better

1. **Native UI** - Linear renders agent progress in issue view automatically
2. **Structured activities** - Thoughts, actions, errors are first-class types
3. **State machine** - Automatic transitions based on emitted activities
4. **Webhooks** - Real-time events for automation
5. **PR linking** - `externalUrls` field natively connects sessions to PRs

## Plan to Linear Issue

### Field Mapping

| Erk Plan Field        | Linear Equivalent                    | Notes                                                             |
| --------------------- | ------------------------------------ | ----------------------------------------------------------------- |
| `plan_identifier`     | `Issue.id`                           | String in Linear, int in GitHub                                   |
| `title`               | `Issue.title`                        | Direct mapping                                                    |
| `body` (plan content) | `Issue.description` or first comment | Same pattern as GitHub                                            |
| `state` (OPEN/CLOSED) | `Issue.state`                        | Linear has richer states (backlog/todo/in_progress/done/canceled) |
| `labels`              | `Issue.labels`                       | Direct mapping                                                    |
| `assignees`           | `Issue.assignee` + subscribers       | Linear is single-assignee                                         |
| `erk-plan` label      | Custom label or Project membership   | Could use either approach                                         |
| `worktree_name`       | Custom field or external             | Not native to Linear                                              |
| `objective_issue`     | Parent issue relationship            | Native sub-issue support                                          |

### Plan Metadata

Erk's `plan-header` metadata fields map to:

| Erk Metadata             | Linear Equivalent                            |
| ------------------------ | -------------------------------------------- |
| `schema_version`         | Not needed (Linear handles schema)           |
| `created_at`             | `Issue.createdAt`                            |
| `created_by`             | `Issue.creator`                              |
| `worktree_name`          | Custom field (Linear doesn't know worktrees) |
| `plan_comment_id`        | Not needed if plan in description            |
| `last_dispatched_*`      | Custom field or AgentSession                 |
| `last_local_impl_*`      | **AgentSession** (native tracking)           |
| `last_remote_impl_at`    | Custom field or AgentSession                 |
| `plan_type`              | Label or custom field                        |
| `source_plan_issues`     | Issue relations                              |
| `objective_issue`        | Parent issue link                            |
| `steps` / `current_step` | Sub-issues or checklist                      |

## Objective to Linear Issue (with label)

User preference: Keep objectives as "special issues", not Projects/Initiatives.

### Mapping

| Erk Objective Concept | Linear Equivalent            |
| --------------------- | ---------------------------- |
| `erk-objective` label | Custom label                 |
| Phases (1A, 1B, 1C)   | Sub-issues or milestones     |
| Roadmap tables        | Issue description (markdown) |
| Action comments       | Comments                     |
| Linked plans          | Child issues (parent-child)  |

Linear's parent-child issue relationships work well for objective to plan hierarchy.

## What Doesn't Map

### Worktree Binding

Linear has no concept of git worktrees. The `worktree_name` field in erk's plan metadata would need to be:

- Stored in a custom field, OR
- Tracked externally by erk

Linear is workspace-scoped, not repository-scoped, so this is a fundamental mismatch.

### Graphite Stacks

Linear doesn't know about Graphite's stacking model. Stack relationships would remain in Graphite's own tracking.

### Cross-Repo Plans

Erk supports plans in a separate repository (`source_repo` field). Linear workspaces are not repository-scoped, so this concept doesn't translate directly.

Options:

- Use Linear Projects to group cross-repo work
- Track repo association in custom field
- Keep cross-repo coordination in GitHub

## Linear Advantages Over GitHub

| Capability            | GitHub Issues      | Linear                             |
| --------------------- | ------------------ | ---------------------------------- |
| Agent as user         | No                 | Yes, first-class with OAuth scopes |
| Pre-formatted context | No, build yourself | Yes, `promptContext` field         |
| Cascading guidance    | No                 | Yes, team/workspace config         |
| Structured activities | No                 | Yes, typed activity stream         |
| Session lifecycle     | No, build yourself | Yes, native 6-state machine        |
| Issue hierarchy       | Partial (2024)     | Yes, native sub-issues             |
| Rich views/filters    | Limited Projects   | Yes, powerful custom views         |
| Workflow automation   | Actions only       | Yes, built-in + webhooks           |

## Implementation Session Flow (Linear)

If erk used Linear for plans, an implementation session would look like:

```
1. User runs `erk implement <issue-id>`
2. erk calls agentSessionCreateOnIssue
3. Linear creates AgentSession (status: pending)
4. Claude Code starts working
5. erk emits AgentActivity for major steps:
   - type: "thought" -> Planning/reasoning
   - type: "action" -> File edits, bash commands
   - type: "elicitation" -> Questions to user
   - type: "response" -> Status updates
   - type: "error" -> Failures
6. User can see progress in Linear UI in real-time
7. On completion, erk updates AgentSession:
   - summary: "Implemented feature X"
   - externalUrls: [PR link]
   - status transitions to complete
8. PR is visible in Linear issue sidebar
```

This is more structured than the current GitHub approach where implementation state is stored in YAML metadata that users never see.

## Guidance as CLAUDE.md Replacement

Linear's guidance system could replace per-repo CLAUDE.md files:

| Erk Concept            | Linear Equivalent           |
| ---------------------- | --------------------------- |
| Repo CLAUDE.md         | Team guidance               |
| Project-specific rules | Team or workspace guidance  |
| Agent behavior config  | Guidance content (markdown) |

Guidance cascades: Workspace to Parent Team to Team, with nearest taking precedence.

## Multi-Backend Architecture

Erk will support both GitHub Issues and Linear as backends for different customers, not migrate from one to the other.

### Gateway Abstraction

The existing gateway pattern (Git, GitHub, Graphite ABCs) extends naturally to issue tracking:

```
IssueTracker ABC
├── GitHubIssueTracker (existing behavior)
└── LinearIssueTracker (new backend)
```

### Backend-Specific Features

| Feature                 | GitHub Backend         | Linear Backend        |
| ----------------------- | ---------------------- | --------------------- |
| Implementation tracking | Metadata blocks (YAML) | AgentSession (native) |
| Activity stream         | Comments               | AgentActivity (typed) |
| Progress visibility     | Collapsed YAML         | Native UI             |
| Worktree binding        | Metadata field         | Custom field          |
| Graphite integration    | Native                 | External tracking     |

### What the Linear Backend Enables

For customers using Linear:

1. **AgentSession for implementation tracking** - Native UI instead of metadata blocks
2. **Typed activities** - Thoughts, actions, errors rendered automatically
3. **Real-time progress** - Users see agent work in Linear UI
4. **Guidance system** - Team-level agent configuration without CLAUDE.md

### What Stays GitHub-Only

Some erk concepts remain GitHub-scoped regardless of issue tracker:

- **Graphite stacks** - PR tooling, not issue tooling
- **Worktree management** - Git operation, backend-agnostic
- **PR creation/sync** - GitHub PRs even if issues are in Linear

### Implementation Approach

1. Extract issue-tracking operations into `IssueTracker` ABC
2. Current GitHub code becomes `GitHubIssueTracker`
3. New `LinearIssueTracker` implements same interface using Linear API
4. Configuration determines which backend to use per-repo or per-workspace
