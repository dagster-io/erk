# Plan: Extract objective-next-plan data fetching into forked Task

## Problem

The `/erk:objective-next-plan` command runs Steps 1–5.5 (issue fetching, validation, roadmap parsing, table display) inline in the main conversation context. Raw JSON from `erk exec get-issue-body` and `erk objective check` consumes main context tokens unnecessarily.

## Approach

Wrap the data-fetching steps in an **inline Task call** within the existing command. No separate agent file needed.

### File to modify

**`.claude/commands/erk/objective-next-plan.md`** — Restructure to delegate Steps 1–4 to a Task agent

### Design

**New Step 1: Parse Arguments** (stays in main — trivial)
- Extract issue number from `$ARGUMENTS` (same logic as current Step 1)
- If no argument, do the branch-detection fallback or prompt

**New Step 2: Launch Task agent** for data fetching
- `subagent_type: "general-purpose"`, `model: "haiku"`
- Task prompt includes all instructions to:
  - Run `erk exec get-issue-body <number>` and validate labels
  - Run `erk exec marker create` for objective-context
  - Run `erk objective check <number> --json-output`
  - Format and return a compact structured summary

**Task agent returns:**

```
OBJECTIVE: #6632 — Codex CLI Adoption Experience
STATUS: OPEN

ROADMAP:
| Step | Phase | Description | Status |
| 1.1 | Phase 1 | Extend capability system... | done (PR #6612) |
| 1.2 | Phase 1 | Create bundled .codex/... | done (PR #6648) |
| 3.1 | Phase 3 | AGENTS.md guidance... | pending |

PENDING_STEPS:
- 1.3: erk init backend selection
- 1.4: Capability install/uninstall dispatches
- 3.1: AGENTS.md / system prompt guidance

RECOMMENDED: 1.3

WARNINGS: (none)
```

**New Step 3: Display and prompt** (main context)
- Display the roadmap table from agent output
- AskUserQuestion for step selection
- Create roadmap-step marker

**Steps 4–7:** Same as current Steps 6–9 (gather context, enter plan mode, save)

### What moves to forked context
- `erk exec get-issue-body` JSON parsing
- Label validation
- `erk objective check --json-output` JSON parsing
- Objective-context marker creation
- Table formatting

### What stays in main context
- Argument parsing (trivial)
- Step selection prompt (AskUserQuestion — requires main context)
- Roadmap-step marker creation
- Plan mode entry and context gathering

## Verification

1. Run `/erk:objective-next-plan 6632` and verify:
   - Roadmap table displays correctly
   - Step selection works
   - Markers are created (`erk exec marker read --session-id ... objective-context`)
   - Plan mode entry works after selection
2. The raw JSON blobs from `get-issue-body` and `objective check` should not appear in main context