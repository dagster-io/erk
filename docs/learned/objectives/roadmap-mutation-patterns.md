---
title: Roadmap Mutation Patterns
read_when:
  - "deciding between surgical vs full-body roadmap updates"
  - "choosing how to update an objective roadmap after a workflow event"
  - "understanding race condition risks in roadmap table mutations"
tripwires:
  - action: "using full-body update for single-cell changes"
    warning: "Full-body updates replace the entire table. For single-cell PR updates, use surgical update (update-roadmap-step) to preserve other cells and avoid race conditions."
  - action: "using surgical update for complete table rewrites"
    warning: "Surgical updates only change one cell. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr)."
  - action: "directly mutating issue body markdown without using either command"
    warning: "Direct body mutation skips status computation. The surgical command writes computed status atomically; bypassing it leaves status stale. See roadmap-mutation-semantics.md."
---

# Roadmap Mutation Patterns

Erk has two distinct strategies for mutating objective roadmap tables, each optimized for different workflow events. Choosing the wrong one creates race conditions or data loss. This document explains **when to use which** and **why the split exists**.

## Why Two Patterns?

The roadmap table is a 4-column markdown table stored in a GitHub issue body. Two fundamentally different mutation shapes arise from different workflow events:

- **Single-cell updates** (plan saved, PR created): Only the PR column of one step changes. The rest of the table — descriptions, other steps, layout — should be untouched. Fetching, parsing, and rewriting the entire table for a single cell change would risk overwriting concurrent edits by other agents or humans.

- **Full-body rewrites** (PR landed): Landing a PR may trigger structural changes — marking a step done, collapsing completed phases, reordering, or adding narrative text. A single-cell regex replacement can't express these layout-level changes.

The split isn't about capability (the full-body approach _could_ do single-cell updates). It's about **blast radius** — a targeted regex replacement can't accidentally destroy unrelated content, while a full rewrite can.

## Decision Table

| Workflow Event              | Pattern   | Why                                                          |
| --------------------------- | --------- | ------------------------------------------------------------ |
| Plan saved to GitHub        | Surgical  | Only the PR cell of one step changes                         |
| PR created from plan        | Surgical  | Only the PR cell of one step changes                         |
| PR landed via `erk land`    | Full-body | May need to restructure phases, update descriptions          |
| Fixing a stale status value | Surgical  | Minimal blast radius for a quick correction                  |
| Restructuring roadmap       | Full-body | Need full control over layout, ordering, and section content |
| Batch status updates        | Full-body | Multiple steps changing simultaneously                       |

## Surgical Update: `update-roadmap-step`

<!-- Source: src/erk/cli/commands/exec/scripts/update_roadmap_step.py, _replace_step_pr_in_body -->

The surgical command finds a step row by ID using regex and replaces **only** the status and PR cells in a single operation. See `_replace_step_pr_in_body()` in `src/erk/cli/commands/exec/scripts/update_roadmap_step.py`.

**Why it writes both status and PR cells:** The command could leave status as `-` and let parse-time inference determine it later. Instead, it computes a display status (`done`, `in-progress`, `pending`) from the PR value and writes it directly. This makes the table human-readable in GitHub's UI without requiring a parse pass. For the full rationale, see [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md).

**Race condition safety:** Because the regex only touches one row's last two cells, concurrent edits to other steps or descriptions are preserved. This is the key advantage over full-body rewrites for single-step changes.

## Full-Body Update: `objective-update-with-landed-pr`

<!-- Source: .claude/commands/erk/objective-update-with-landed-pr.md:1-50 -->

The full-body update is orchestrated by a Claude command (not a Python script). It fetches context via `objective-update-context`, then delegates to a subagent that:

1. Analyzes which roadmap steps the landed PR completed
2. Performs prose reconciliation (checks Design Decisions, Implementation Context, step descriptions for staleness)
3. Composes an action comment documenting the change (with optional Body Reconciliation subsection)
4. Rewrites the entire objective body with updated roadmap and reconciled prose
5. Posts both the comment and updated body

**Why agent-driven instead of a script:** Landing a PR requires _judgment_ — the step description might need updating if the PR scope differs, completed phases might need collapsing, Design Decisions might need revision, and Implementation Context might need correction. These decisions don't reduce to mechanical regex.

**Race condition risk:** The entire issue body is fetched, modified, and written back. Any edits made between fetch and write are lost. This is acceptable because:

- PR landing is an infrequent event (not concurrent with other mutations)
- The alternative — surgical edits for each sub-change — would require multiple API calls with the same race window each time
- The action comment provides an audit trail if anything goes wrong

## The Context-Fetching Pattern

<!-- Source: src/erk/cli/commands/exec/scripts/objective_update_context.py, objective_update_context -->

The full-body workflow uses a **bundled context fetch** (`erk exec objective-update-context`) to retrieve the objective issue, plan issue, and PR details in a single CLI call. This exists because the subagent needs all three to compose the update, and fetching them in separate LLM turns would waste tokens and add latency. See `objective_update_context()` in `src/erk/cli/commands/exec/scripts/objective_update_context.py`.

## Integration Points

Both patterns are triggered by upstream workflow commands, not invoked directly by users:

| Upstream Command | Triggers                     | Via                                                             |
| ---------------- | ---------------------------- | --------------------------------------------------------------- |
| `erk plan save`  | Surgical update to link plan | Skill calls `update-roadmap-step` with plan reference           |
| `erk pr submit`  | Surgical update to link PR   | Skill calls `update-roadmap-step` with PR reference             |
| `erk land`       | Full-body update after merge | Helpers in `objective_helpers.py` detect objective, prompt user |

<!-- Source: src/erk/cli/commands/objective_helpers.py, prompt_objective_update -->

See `prompt_objective_update()` in `src/erk/cli/commands/objective_helpers.py` for how `erk land` discovers the linked objective and offers to run the full-body update.

## Prose Reconciliation

The full-body update now includes **prose reconciliation** — the subagent doesn't just update roadmap mechanics, it also audits the objective's reconcilable sections (Design Decisions, Implementation Context, step descriptions) against what the PR actually implemented. If any prose is stale, the subagent corrects it in the body update and documents the changes in a "Body Reconciliation" subsection of the action comment.

This is the key innovation: body mutations are no longer limited to roadmap table mechanics. The LLM agent actively maintains the accuracy of the objective's prose sections, preventing the "silent staleness" problem where objectives describe outdated architecture or overridden decisions.

## Anti-Patterns

**WRONG: Calling `update-roadmap-step` after landing a PR.** The surgical command only updates PR and status cells. After landing, you often need to update descriptions, restructure phases, or add completion notes. Use the full-body workflow.

**WRONG: Using full-body rewrite to link a plan to a step.** The full-body approach fetches, parses, and regenerates the entire body — unnecessary for a single cell change and risks overwriting concurrent edits. Use the surgical command.

**WRONG: Directly editing the issue body markdown without using either command.** Direct mutation skips status computation entirely. If you set the PR cell to `#123` but leave status at `pending`, the table is inconsistent until the next parse. See [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) for the write-vs-read asymmetry.

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — Write-time status computation vs parse-time inference
- [Roadmap Status System](roadmap-status-system.md) — Two-tier status resolution rules
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — LBYL error patterns used by both commands
