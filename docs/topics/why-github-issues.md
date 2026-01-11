# Why GitHub Issues for Plans

Why erk stores plans as GitHub issues rather than markdown files in the repository.

## The Problem

AI agents need persistent, resumable plans. When an agent is interrupted mid-task—whether by context limits, errors, or intentional handoffs—it needs somewhere to resume from. The question: where should these plans live?

## The Origin Story: Markdown Files Didn't Work

Erk originally stored plans as markdown files committed to the repository. This seemed natural—plans are text, repositories hold text.

The pain point emerged with worktrees. Erk uses git worktrees for parallel development: each plan executes in an isolated worktree. When plans lived in the repo, moving between worktrees meant copying files, merging changes, and tracking which worktree had the "real" plan. It was messy and error-prone.

The insight: worktrees are ephemeral; plans need to outlive them. A worktree might be deleted after a PR merges, but the plan's history should persist. Plans aren't source code—they're entities that track work across the codebase's evolution.

## The Data Model Fit

GitHub Issues implement exactly the data model plans need:

### Issue as Entity

Each plan is discrete and addressable. It has a stable identity (issue number, URL) that persists regardless of which worktree or branch is active. You can reference plan #123 from anywhere.

### Labels for Classification

Structured metadata without schema rigidity. Erk uses labels like `erk-plan`, `erk-objective`, and `erk-extraction` to categorize without a rigid database schema. Adding new plan types means adding new labels.

### Two-Part Schema

Erk splits plan content between the issue body and the first comment:

| Location      | Content           | Purpose              |
| ------------- | ----------------- | -------------------- |
| Issue body    | Metadata block    | Fast queries via API |
| First comment | Full plan content | Detail when needed   |

This optimizes GitHub API performance. Listing plans only fetches issue bodies; full content is fetched on demand.

### Comment Stream as Immutable Log

Comments are append-only. When an agent starts implementation, it adds a comment. When it completes, another comment. When a human provides feedback, another comment. This creates an audit trail that can't be rewritten—you can see exactly how a plan evolved.

## Workflow Integration

GitHub Issues integrate with workflows that already exist:

**PR-to-issue linking**: A PR body containing `Closes #123` automatically closes the plan issue when the PR merges. No manual bookkeeping.

**GitHub Actions**: Workflows can trigger on issue state transitions. Open a plan → start implementation. Close an issue → clean up worktrees.

**Existing ecosystem**: Notifications, permissions, search, mobile apps—all work out of the box. No custom infrastructure to maintain.

## Lifecycle Mapping

Issue states map naturally to plan lifecycle:

| Issue State | Plan Meaning                        |
| ----------- | ----------------------------------- |
| Open        | Active or queued for implementation |
| Assigned    | Claimed by an agent or person       |
| Closed      | Completed or cancelled              |

This isn't a forced mapping—it's how people already think about work items. A plan progresses from open to implemented to merged, just like any ticket.

## The Hierarchy Pattern

Plans often belong to larger efforts. Erk supports this through _objectives_—parent issues that track multiple related plans:

```
Objective #100: "Improve authentication"
├── Plan #101: "Add OAuth support"
├── Plan #102: "Implement rate limiting"
└── Plan #103: "Add session management"
```

Each plan's metadata includes an `objective_issue` field linking to its parent. Most ticketing systems support this pattern (epics, sub-tasks, parent issues)—GitHub Issues handles it naturally.

## Plans as Context Graphs

The most powerful aspect of issue-based plans is what they accumulate over time.

### Rules vs. Decision Traces

The plan schema defines what _should_ happen—the implementation steps, success criteria, constraints. The comment stream records what _actually_ happened—the decisions made, blockers hit, workarounds discovered.

[Foundation Capital's "context graphs" concept](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) captures this distinction. AI systems need both rules (what to do) and decision traces (what was done and why). A plan issue provides both in one artifact.

### Why Files Fail, Issues Succeed

A markdown file captures state: "here is the plan." An issue with comments captures _lineage_: the progression of decisions, not just the outcome. You can see that step 3 was harder than expected, that the agent tried approach A before switching to B, that a human suggested the workaround in step 5.

### Organizational Memory for Agents

Past plans become queryable precedent. When an agent encounters an edge case—"how do I handle rate limiting in this codebase?"—it can search previous plans for patterns. The comment streams show not just what was done, but what problems arose and how they were resolved.

### Immutability Matters

Comments are append-only. Agents can trust the history won't be rewritten. This is the difference between a "task tracker" and a "decision trace system." Each comment is a permanent record of a decision point.

## Looking Forward: Beyond GitHub

GitHub Issues is one implementation of this pattern. The underlying abstraction is:

- **Entity**: Discrete, addressable, with stable identity
- **Metadata**: Structured fields for fast queries
- **Log**: Append-only history of activities
- **Lifecycle**: States that map to workflow stages
- **Hierarchy**: Parent-child relationships between entities

Other systems implement this pattern differently. Linear's agent-first primitives (AgentSession, activities) show the pattern generalizing beyond traditional ticketing. The concept is portable even if specific implementations aren't yet.

## Conclusion

GitHub Issues weren't designed for AI agent workflows. But they implement the context graph pattern that agent workflows need: entities with identity, metadata for queries, append-only logs for decision traces, and lifecycle states for coordination.

The "accidental architecture" turned out to be right. Rather than building custom plan infrastructure, erk leverages infrastructure that already exists, already scales, and already integrates with developer workflows.

## See Also

- [The Workflow](the-workflow.md) - How plans fit into the complete workflow
- [Plan-Oriented Engineering](plan-oriented-engineering.md) - The philosophy behind planning first
- [Plan Mode](plan-mode.md) - How Claude Code creates plans
