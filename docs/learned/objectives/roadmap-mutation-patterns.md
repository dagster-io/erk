---
title: Roadmap Mutation Patterns
read_when:
  - "deciding between surgical vs full-body roadmap updates"
  - "choosing how to update an objective roadmap after a workflow event"
  - "understanding race condition risks in roadmap table mutations"
tripwires:
  - action: "using full-body update for single-cell changes"
    warning: "Full-body updates replace the entire table. For single-node PR updates, use surgical update (update-objective-node) to preserve other cells and avoid race conditions."
  - action: "using surgical update for complete table rewrites"
    warning: "Surgical updates only change one node. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr)."
  - action: "directly mutating issue body markdown without using either command"
    warning: "Direct body mutation skips status computation. The surgical command writes computed status atomically; bypassing it leaves status stale. See roadmap-mutation-semantics.md."
  - action: "using None/empty string interchangeably in update-objective-node parameters"
    warning: "None=preserve existing value, empty string=clear the cell, value=set new value. Confusing these leads to accidental data loss or stale values."
last_audited: "2026-02-25 18:00 PT"
audit_result: edited
---

# Roadmap Mutation Patterns

Erk has two distinct strategies for mutating objective roadmap tables, each optimized for different workflow events. Choosing the wrong one creates race conditions or data loss. This document explains **when to use which** and **why the split exists**.

## Why Two Patterns?

The roadmap table is a 4-column markdown table stored in a GitHub issue comment (`| Node | Description | Status | PR |`). The YAML frontmatter in the issue body is the source of truth; the comment table is a rendered view. Two fundamentally different mutation shapes arise from different workflow events:

- **Single-node updates** (plan saved, PR created): Only the status/PR of one step changes. The YAML frontmatter is updated surgically, then the comment table is deterministically re-rendered from YAML.

- **Full-body rewrites** (PR landed): Landing a PR may trigger structural changes — marking multiple steps done, updating descriptions, or adding narrative text. The `objective-apply-landed-update` command handles batch updates.

## Decision Table

| Workflow Event              | Pattern   | Why                                                          |
| --------------------------- | --------- | ------------------------------------------------------------ |
| Plan saved to GitHub        | Surgical  | Only the status of one step changes to in_progress           |
| PR created from plan        | Surgical  | Only the PR cell of one step changes                         |
| PR landed via `erk land`    | Full-body | May need to mark multiple nodes done                         |
| Fixing a stale status value | Surgical  | Minimal blast radius for a quick correction                  |
| Restructuring roadmap       | Full-body | Need full control over layout, ordering, and section content |
| Batch status updates        | Full-body | Multiple steps changing simultaneously                       |

## Surgical Update: `update-objective-node`

<!-- Source: src/erk/cli/commands/exec/scripts/update_objective_node.py -->

The surgical command updates YAML frontmatter for specific node(s) and then deterministically re-renders the comment table using `rerender_comment_roadmap()`. It accepts `--node` flags (one or more) and `--pr`/`--status` options.

**How it works:**

1. Updates the YAML frontmatter via `update_node_in_frontmatter()` for each specified node
2. Serializes the updated YAML back into the metadata block and replaces it in the issue body
3. Writes the updated issue body to GitHub
4. Re-renders the comment table from the updated YAML using `rerender_comment_roadmap()`

**Race condition safety:** Because the YAML update only touches specific node entries, concurrent edits to other nodes or descriptions are preserved. The comment table re-render is deterministic from YAML, so it always reflects the current state.

## Full-Body Update: `objective-apply-landed-update`

<!-- Source: src/erk/cli/commands/exec/scripts/objective_apply_landed_update.py -->

The full-body update is handled by `objective-apply-landed-update`, which combines fetch-context, update-nodes, and post-action-comment in a single call. The caller specifies which nodes to mark done via `--node` flags.

1. Fetches objective, plan, and PR context
2. Updates specified nodes to done with PR reference
3. Re-renders the comment table from updated YAML
4. Posts an action comment documenting the change
5. Returns rich JSON for the agent to use in prose reconciliation

**Why a single script:** Combining all mechanical steps in one command eliminates 5+ sequential agent commands and reduces API calls.

## The Context-Fetching Pattern

<!-- Source: src/erk/cli/commands/exec/scripts/objective_fetch_context.py -->

The full-body workflow uses a **bundled context fetch** (`erk exec objective-fetch-context`) to retrieve the objective issue, plan issue, and PR details in a single CLI call. This exists because the command needs all three to compose the update, and fetching them in separate LLM turns would waste tokens and add latency.

## Integration Points

Both patterns are triggered by upstream workflow commands, not invoked directly by users:

| Upstream Command | Triggers                                | Via                                                   |
| ---------------- | --------------------------------------- | ----------------------------------------------------- |
| `erk plan save`  | Surgical update to set node in_progress | Skill calls `update-objective-node` with status       |
| `erk pr submit`  | Surgical update to link PR              | Skill calls `update-objective-node` with PR reference |
| `erk land`       | Full-body update after merge            | `objective-apply-landed-update` with `--node` flags   |

## Anti-Patterns

**WRONG: Calling `update-objective-node` after landing a PR.** The surgical command only updates specified nodes. After landing, use `objective-apply-landed-update` which also posts action comments.

**WRONG: Using full-body rewrite to link a plan to a step.** The full-body approach is unnecessary for a single node change and risks overwriting concurrent edits. Use the surgical command.

**WRONG: Directly editing the issue body markdown without using either command.** Direct mutation skips status computation entirely. If you set the PR cell to `#123` but leave status at `pending`, the table is inconsistent. See [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) for the write-vs-read asymmetry.

## Comment Table Re-rendering

The comment table (visible in the GitHub UI) is re-rendered deterministically from YAML frontmatter using `rerender_comment_roadmap()`. This function:

1. Parses nodes from YAML frontmatter in the issue body
2. Groups nodes by phase
3. Enriches phase names from markdown headers in the comment
4. Renders fresh markdown tables
5. Splices the new tables into the comment's `<!-- erk:roadmap-table -->` marker-bounded section

This replaced the previous approach of per-node regex patching, which was fragile and couldn't handle column layout changes.

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — Write-time status computation vs parse-time inference
- [Roadmap Status System](roadmap-status-system.md) — Two-tier status resolution rules
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — LBYL error patterns used by both commands
