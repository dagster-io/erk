# Why GitHub Issues for Plans

Why erk stores plans as GitHub issues rather than markdown files in the repository.

## The Origin Story: Markdown Files Didn't Work

`erk` originated as a worktree management tool. Users were heavily using plans as well, but managing and coordinating them became burdensome. They were manually saving markdown files on disk, checking them in, copying them between worktrees, and so forth.

GitHub Issues were a simple, available, and convenient way to store these markdown documents and have them available across worktrees. But nearly all their features turned out to be applicable to plans—linkage to PRs, comments for context, labels for classification.

## The Data Model Fit

GitHub Issues have a number of features applicable to plan management: document storage, labeling, attribution, comments as an update stream, and integration with developer-centric workflows. By utilizing these features, `erk` uses GitHub Issues as a database of plans and other related entities.

### Issue as Entity

Each plan is discrete and addressable. It has a stable identity (issue number, URL) that persists regardless of which worktree or branch is active. You can reference plan #123 from anywhere, and it has well-known APIs and tools (such as `gh`) for querying its content.

### Labels for Classification

Structured metadata without schema rigidity. `erk` uses labels like `erk-plan` to categorize without a rigid database schema. Adding new plan types and concepts means adding new labels.

### Comment Stream as Immutable Log

`erk` treats comments as an append-only log of updates where one can record the prompts that led to a plan, track progress, add context, and so forth. When an agent starts implementation, it adds a comment. When it completes, another comment. When a human provides feedback, another comment. This creates an audit trail that can't be rewritten—you can see exactly how a plan evolved from ideation to completion.

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

Plans often belong to larger efforts. `erk` supports this through _objectives_—parent issues that track multiple related plans:

```
Objective #100: "Improve authentication"
├── Plan #101: "Add OAuth support"
├── Plan #102: "Implement rate limiting"
└── Plan #103: "Add session management"
```

Each plan's metadata includes an `objective_issue` field linking to its parent. Most ticketing systems support this pattern (epics, sub-tasks, parent issues) and it is applicable to objectives, plans and other future use cases.

## Plans as Context Graphs

The most powerful aspect of issue-based plans is what they accumulate over time.

### Rules vs. Decision Traces

The plan schema defines what _should_ happen—the implementation steps, success criteria, constraints. The comment stream records what _actually_ happened—the decisions made, blockers hit, workarounds discovered.

[Foundation Capital's "context graphs" concept](https://foundationcapital.com/context-graphs-ais-trillion-dollar-opportunity/) captures this distinction. AI systems need both rules (what to do) and decision traces (what was done and why). A plan issue provides both in one artifact.

### System of Record for Agentic Engineering

Past plans become queryable precedent. When an agent encounters an edge case—"how do I handle rate limiting in this codebase?"—it can search previous plans for patterns. The comment streams show not just what was done, but what problems arose and how they were resolved. We can query historical plans and the outcomes they generated to improve future outcomes in the codebase.

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
