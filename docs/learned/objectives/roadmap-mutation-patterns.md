---
title: Roadmap Mutation Patterns
read_when:
  - "deciding between surgical vs full-body roadmap updates"
  - "choosing how to update an objective roadmap after a workflow event"
  - "understanding race condition risks in roadmap table mutations"
tripwires:
  - action: "using full-body update for single-cell changes"
    warning: "Full-body updates replace the entire table. For single-cell PR updates, use surgical update (update-objective-node) to preserve other cells and avoid race conditions."
  - action: "using surgical update for complete table rewrites"
    warning: "Surgical updates only change one cell. For rewriting roadmaps after landing PRs (status + layout changes), use full-body update (objective-update-with-landed-pr)."
  - action: "directly mutating issue body markdown without using either command"
    warning: "Direct body mutation skips status computation. The surgical command writes computed status atomically; bypassing it leaves status stale. See roadmap-mutation-semantics.md."
  - action: "writing regex patterns to match roadmap table rows without ^ and $ anchors"
    warning: "All roadmap table row regex patterns MUST use ^...$ anchors with re.MULTILINE. Without anchors, patterns can match partial lines or span rows."
  - action: "using None/empty string interchangeably in update-objective-node parameters"
    warning: "None=preserve existing value, empty string=clear the cell, value=set new value. Confusing these leads to accidental data loss or stale values."
last_audited: "2026-02-16 14:20 PT"
audit_result: edited
---

# Roadmap Mutation Patterns

Erk has two distinct strategies for mutating objective roadmap tables, each optimized for different workflow events. Choosing the wrong one creates race conditions or data loss. This document explains **when to use which** and **why the split exists**.

## Why Two Patterns?

The roadmap table is a 5-column markdown table stored in a GitHub issue body (`| Node | Description | Status | Plan | PR |`). Two fundamentally different mutation shapes arise from different workflow events:

- **Single-step updates** (plan saved, PR created): Only the plan/PR columns of one step change. The rest of the table — descriptions, other steps, layout — should be untouched. Fetching, parsing, and rewriting the entire table for a single step change would risk overwriting concurrent edits by other agents or humans.

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

## Surgical Update: `update-objective-node`

<!-- Source: src/erk/cli/commands/exec/scripts/update_objective_node.py, _replace_node_refs_in_body -->

The surgical command finds a step row by ID using regex and replaces **only** the status, plan, and PR cells in a single operation. See `_replace_node_refs_in_body()` in `src/erk/cli/commands/exec/scripts/update_objective_node.py`.

**Why it writes status, plan, and PR cells:** The command could leave status as `-` and let parse-time inference determine it later. Instead, it computes a display status (`done`, `in-progress`, `pending`) from the plan/PR values and writes it directly. Setting `--pr` automatically clears the plan column, and vice versa. This makes the table human-readable in GitHub's UI without requiring a parse pass. For the full rationale, see [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md).

**Race condition safety:** Because the regex only touches one row's last three cells, concurrent edits to other steps or descriptions are preserved. This is the key advantage over full-body rewrites for single-step changes.

## Full-Body Update: `objective-update-with-landed-pr`

<!-- Source: .claude/commands/erk/objective-update-with-landed-pr.md:1-50 -->

The full-body update is orchestrated by a Claude command (not a Python script). It fetches context via `objective-fetch-context`, then performs all steps inline:

1. Analyzes which roadmap steps the landed PR completed
2. Composes an action comment documenting the change
3. Rewrites the entire objective body with updated roadmap
4. Posts both the comment and updated body

**Why agent-driven instead of a script:** Landing a PR requires _judgment_ — the step description might need updating if the PR title differs, completed phases might need collapsing, and the "Current Focus" section needs to shift to the next pending step. These decisions don't reduce to mechanical regex.

**Race condition risk:** The entire issue body is fetched, modified, and written back. Any edits made between fetch and write are lost. This is acceptable because:

- PR landing is an infrequent event (not concurrent with other mutations)
- The alternative — surgical edits for each sub-change — would require multiple API calls with the same race window each time
- The action comment provides an audit trail if anything goes wrong

## The Context-Fetching Pattern

<!-- Source: src/erk/cli/commands/exec/scripts/objective_fetch_context.py, objective_fetch_context -->

The full-body workflow uses a **bundled context fetch** (`erk exec objective-fetch-context`) to retrieve the objective issue, plan issue, and PR details in a single CLI call. This exists because the command needs all three to compose the update, and fetching them in separate LLM turns would waste tokens and add latency. See `objective_fetch_context()` in `src/erk/cli/commands/exec/scripts/objective_fetch_context.py`.

## Integration Points

Both patterns are triggered by upstream workflow commands, not invoked directly by users:

| Upstream Command | Triggers                     | Via                                                             |
| ---------------- | ---------------------------- | --------------------------------------------------------------- |
| `erk plan save`  | Surgical update to link plan | Skill calls `update-objective-node` with plan reference         |
| `erk pr submit`  | Surgical update to link PR   | Skill calls `update-objective-node` with PR reference           |
| `erk land`       | Full-body update after merge | Helpers in `objective_helpers.py` detect objective, prompt user |

<!-- Source: src/erk/cli/commands/objective_helpers.py, prompt_objective_update -->

See `prompt_objective_update()` in `src/erk/cli/commands/objective_helpers.py` for how `erk land` discovers the linked objective and offers to run the full-body update.

## Anti-Patterns

**WRONG: Calling `update-objective-node` after landing a PR.** The surgical command only updates PR and status cells. After landing, you often need to update descriptions, restructure phases, or add completion notes. Use the full-body workflow.

**WRONG: Using full-body rewrite to link a plan to a step.** The full-body approach fetches, parses, and regenerates the entire body — unnecessary for a single cell change and risks overwriting concurrent edits. Use the surgical command.

**WRONG: Directly editing the issue body markdown without using either command.** Direct mutation skips status computation entirely. If you set the PR cell to `#123` but leave status at `pending`, the table is inconsistent until the next parse. See [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) for the write-vs-read asymmetry.

## Regex Anchoring for Table Row Matching

All regex patterns that match roadmap table rows MUST use `^...$` anchors with `re.MULTILINE`. Without anchors, patterns can match partial lines or span multiple rows, causing incorrect mutations.

The canonical example is `_replace_node_refs_in_body()` in `src/erk/cli/commands/exec/scripts/update_objective_node.py`, which builds a compiled regex anchored with `^...$` and `re.MULTILINE` to match a single 5-column row by step ID. Each cell is captured as a non-greedy group so only the target row's status/plan/PR cells are replaced.

**Why anchoring matters**: Without `^` and `$` anchors, a pattern like `\|[^|]+\|` could match across row boundaries. The `re.MULTILINE` flag makes `^` and `$` match at line starts/ends rather than just string starts/ends.

**Pattern**: Every regex that operates on markdown table rows should follow: anchored `^...$` with `re.MULTILINE`.

## Related Documentation

- [Roadmap Mutation Semantics](../architecture/roadmap-mutation-semantics.md) — Write-time status computation vs parse-time inference
- [Roadmap Status System](roadmap-status-system.md) — Two-tier status resolution rules
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — LBYL error patterns used by both commands
