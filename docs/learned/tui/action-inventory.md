---
title: TUI Command Architecture
read_when:
  - "adding a new command to the TUI or desktop dashboard"
  - "understanding how command availability is determined"
  - "choosing which execution pattern a new command should use"
tripwires:
  - action: "adding a command without an availability predicate"
    warning: "Every command needs an is_available predicate based on PlanRowData field presence. Commands without predicates appear when they can't execute."
  - action: "adding an ACTION command that executes instantly"
    warning: "ACTION category implies mutative operations. Instant operations belong in OPEN or COPY categories."
last_audited: "2026-02-08 00:00 PT"
audit_result: edited
---

# TUI Command Architecture

The TUI command system uses a data-driven registry pattern where commands declare their own availability based on `PlanRowData` field presence. This decouples command definitions from UI rendering, enabling the same registry to serve multiple frontends (TUI command palette, desktop toolbar).

## Why Data-Driven Availability

<!-- Source: src/erk/tui/commands/registry.py, get_all_commands -->

Commands don't check "can I run?" at execution time — they declare upfront what data they need via `is_available` predicates. This design was chosen because:

1. **Multiple consumers need the same logic.** The TUI command palette (`MainListCommandProvider`, `PlanCommandProvider`) and the desktop dashboard toolbar both need to know which actions are valid for a given row. Centralizing predicates in the registry avoids duplicating availability logic across frontends.

2. **Availability depends on `PlanRowData` nullability.** Each `PlanRowData` field is nullable for a reason (no PR yet, no workflow run, etc.). The predicates express which combination of non-null fields a command requires. This makes the availability contract explicit and testable.

3. **Commands that are always available use `lambda _: True`** — these are plan-level operations (close, prepare, submit) that only need the issue number, which is always present.

## Category-to-Execution Pattern Mapping

Categories are not just cosmetic labels — they correlate strongly with execution characteristics:

| Category | Execution Pattern                       | Latency    | Side Effects                               |
| -------- | --------------------------------------- | ---------- | ------------------------------------------ |
| ACTION   | In-process HTTP or subprocess streaming | 500ms–600s | Mutates GitHub state or triggers workflows |
| OPEN     | Browser launch                          | Instant    | None (navigates browser)                   |
| COPY     | Clipboard write                         | Instant    | None (copies to clipboard)                 |

The key insight is within ACTION: some actions (close, submit) are fast in-process HTTP calls to the GitHub API, while others (land, fix-conflicts, address) are long-running subprocess commands with streaming output. The distinction matters because streaming commands need the `repo_root` capability marker and the full cross-thread UI update pipeline described in [streaming-output.md](streaming-output.md).

## Availability Predicate Patterns

<!-- Source: src/erk/tui/commands/registry.py, get_all_commands -->

Commands fall into four availability tiers:

| Tier               | Predicate                | Commands                                                                       | Rationale                                                |
| ------------------ | ------------------------ | ------------------------------------------------------------------------------ | -------------------------------------------------------- |
| Always available   | `lambda _: True`         | close_plan, copy_prepare, copy_prepare_activate, copy_submit                   | Only need `issue_number`, which is always present        |
| Needs issue URL    | `issue_url is not None`  | submit_to_queue, copy_replan                                                   | Requires the issue to exist on GitHub (not just locally) |
| Needs PR           | `pr_number is not None`  | fix_conflicts_remote, address_remote, open_pr, copy_checkout, copy_pr_checkout | PR must be linked to the plan                            |
| Compound condition | Multiple fields non-null | land_pr (needs PR + OPEN state + run URL)                                      | Landing requires all CI infrastructure to be present     |

**Anti-pattern**: Writing `is_available=lambda ctx: True` for a command that uses `ctx.row.pr_number`. The predicate will allow execution when `pr_number` is None, causing a runtime error. This is why the [three-layer null validation](adding-commands.md) pattern exists — the predicate is necessary but not sufficient.

## Cross-Frontend Command Reuse

The registry serves as a shared contract between the TUI and desktop dashboard:

- **TUI**: `MainListCommandProvider` and `PlanCommandProvider` iterate `get_available_commands()`, formatting each as a `DiscoveryHit` or `Hit` for Textual's command palette.
- **Desktop dashboard**: The toolbar reads the same availability logic to enable/disable buttons. See [interaction-model.md](../desktop-dash/interaction-model.md) for how desktop diverges from TUI conventions.

This shared registry means adding a command to the TUI automatically makes it available for the desktop dashboard to adopt — the availability logic doesn't need to be re-implemented.

## Related Documentation

- [Adding Commands to TUI](adding-commands.md) — Step-by-step process and three-layer null validation
- [Command Execution Strategies](command-execution.md) — Streaming vs executor patterns, stdin deadlock prevention
- [TUI Streaming Output](streaming-output.md) — Cross-thread UI updates for long-running commands
- [TUI Data Contract](data-contract.md) — PlanRowData fields that predicates evaluate
- [Desktop Dashboard Interaction Model](../desktop-dash/interaction-model.md) — How the same commands map to desktop GUI
