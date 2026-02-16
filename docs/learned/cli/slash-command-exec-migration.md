---
title: Slash Command to Exec Migration
last_audited: "2026-02-16 00:00 PT"
audit_result: clean
read_when:
  - "adding business logic to a slash command"
  - "deciding whether to call gh/git directly from a slash command or extract to exec"
  - "creating a new slash command that needs to interact with GitHub or git"
tripwires:
  - action: "adding inline shell logic to a slash command instead of using erk exec"
    warning: "Extract reusable logic to an erk exec command. Slash commands should orchestrate exec calls, not contain business logic."
  - action: "calling gh or git directly from a slash command"
    warning: "Use an erk exec script instead. Direct CLI calls bypass gateways, making the logic untestable and unreusable."
---

# Slash Command to Exec Migration

## The Architectural Boundary

Slash commands (`.claude/commands/`) and exec scripts (`src/erk/cli/commands/exec/scripts/`) serve different roles in erk's agent architecture. The boundary between them is the key insight:

- **Slash commands** are orchestration layers for Claude. They parse arguments, chain `erk exec` calls, format output for the agent, and suggest next steps. They contain no business logic.
- **Exec scripts** are testable Python behind the gateway pattern. They use dependency injection via Click context, return structured JSON, and are reusable by any caller (slash commands, hooks, CI, TUI).

This separation exists because slash commands execute as natural language instructions inside Claude's context — they can't be unit-tested, type-checked, or faked. Anything that touches GitHub, git, or the filesystem should live in an exec script where it goes through gateways.

## Why Not Just Call `gh` Directly?

The tempting shortcut is `gh issue view 123 --json body -q .body` inside a slash command. This fails for three reasons:

1. **Untestable** — Slash command logic can't be covered by the fake-driven test architecture. Exec scripts use gateway abstractions with fake implementations.
2. **Unreusable** — The same GitHub query may be needed by other slash commands, hooks, or CI. An exec script is callable from all of these; inline `gh` is locked inside one command.
3. **Fragile parsing** — Raw `jq` parsing in markdown breaks silently. Exec scripts return typed JSON with explicit success/error structures, following the [discriminated union pattern](../architecture/discriminated-union-error-handling.md).

## Recognizing Migration Candidates

Slash commands that need extraction share these symptoms:

| Symptom                             | Example                                | Why It's a Problem                    |
| ----------------------------------- | -------------------------------------- | ------------------------------------- |
| Direct `gh` or `git` calls          | `gh api repos/.../pulls/123`           | Bypasses gateways                     |
| JSON parsing with `jq`              | `--json body -q .body`                 | Fragile, untestable                   |
| Conditional logic on command output | "If the command returns X, then..."    | Business logic in orchestration layer |
| Duplicated across commands          | Same `gh` call in 3 different commands | Violates single-source principle      |

## The Extraction Pattern

### 1. Create the exec script

<!-- Source: src/erk/cli/commands/exec/scripts/get_issue_body.py, get_issue_body -->

See `get_issue_body()` in `src/erk/cli/commands/exec/scripts/get_issue_body.py` for a minimal example showing the full pattern: Click command with context injection, gateway usage, and JSON output with success/error discrimination.

### 2. Register statically in the exec group

<!-- Source: src/erk/cli/commands/exec/group.py, exec_group -->

Registration is a manual import-and-add in `src/erk/cli/commands/exec/group.py` — not auto-discovered. Missing this step means the command exists but isn't callable.

### 3. Replace inline logic in the slash command

The slash command becomes a thin orchestration layer that calls `erk exec`, parses JSON output, and formats results for the agent.

<!-- Source: .claude/commands/erk/plan-save.md, Steps 2-4 -->

See `.claude/commands/erk/plan-save.md` for a multi-step orchestration example: it chains `plan-save-to-issue`, `get-plan-metadata`, and `update-roadmap-step` calls with error handling between steps.

<!-- Source: .claude/commands/local/quick-submit.md -->

See `.claude/commands/local/quick-submit.md` for the simplest case: a single `erk exec quick-submit` delegation with no additional orchestration.

## Graduation: Exec to Top-Level CLI

Some exec commands outgrow their hidden status and become top-level CLI commands (e.g., `erk exec objective-roadmap-check` graduated to `erk objective check`). This happens when:

- The command is useful to humans, not just agents
- It needs aliases or richer flag support
- Shared parsing logic emerges (extracted to a `_shared.py` module)

The graduated command typically keeps `--json-output` for programmatic callers while gaining human-friendly display modes.

## Historical Context: PR #6328

PR #6328 demonstrated the pattern at scale by migrating objective roadmap operations from inline `gh api` calls to exec commands. The shared parsing logic was extracted to `objective_roadmap_shared.py`, enabling both the query command (`objective-roadmap-check`) and the mutation command (`update-roadmap-step`) to share roadmap parsing without duplication.

## Related Documentation

- [erk exec Commands](erk-exec-commands.md) — Command reference and format flag support
- [Discriminated Union Error Handling](../architecture/discriminated-union-error-handling.md) — The success/error type pattern used by exec scripts
