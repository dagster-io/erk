---
title: Objective Summary Format
last_audited: "2026-02-08 13:55 PT"
audit_result: edited
read_when:
  - working with objective-next-plan command or objective-view command
  - modifying how objective context flows between agents
  - changing roadmap status inference logic
  - parsing objective summary JSON output
tripwires:
  - action: "adding a new roadmap status value"
    warning: "Status inference lives in two places that must stay synchronized: the roadmap parser (objective_roadmap_shared.py) and the agent prompt in objective-next-plan.md. Update both or the formats will diverge."
---

# Objective Summary Format

Objective data flows through two distinct formats depending on the consumer. Understanding which format to use — and why they differ — prevents agents from mixing them up or building against the wrong contract.

## Two Formats, Two Purposes

Objective context reaches consumers through two separate paths, each with its own format:

| Consumer                          | Format                                     | Source of truth                                             | Why this format                                                          |
| --------------------------------- | ------------------------------------------ | ----------------------------------------------------------- | ------------------------------------------------------------------------ |
| Claude agent (parent context)     | Structured text (OBJECTIVE/ROADMAP/etc.)   | `.claude/commands/erk/objective-next-plan.md` Step 2 prompt | Optimized for LLM parsing — flat sections, no nested JSON to deserialize |
| Programmatic tools (scripts, CLI) | JSON with `phases`, `summary`, `next_step` | `erk objective check --json-output`                         | Machine-readable for field extraction and validation                     |

These formats exist independently because their consumers have fundamentally different parsing capabilities. The agent text format uses labeled sections (OBJECTIVE, STATUS, ROADMAP, PENDING_STEPS, RECOMMENDED) that a haiku subagent can reliably produce. The programmatic JSON format uses typed fields with nested phase/step structures that code can traverse.

**Anti-pattern:** Asking a Task agent to return the `erk objective check --json-output` format directly. The JSON output has deeply nested phases with validation metadata that agents don't need and can't reliably produce. Use the text format for agent-to-agent communication.

## Agent Text Format Specification

<!-- Source: .claude/commands/erk/objective-next-plan.md, Step 2 -->

Task agents delegated for objective context must return structured output with five labeled sections. The canonical format is defined in the `objective-next-plan.md` command prompt (Step 2). The sections are:

1. **OBJECTIVE** — issue number, title (format: `OBJECTIVE: #<number> — <title>`)
2. **STATUS** — issue state (`OPEN` or `CLOSED`)
3. **ROADMAP** — markdown table with columns: Step, Phase, Description, Status (including PR references where applicable)
4. **PENDING_STEPS** — bullet list of steps with status "pending"
5. **RECOMMENDED** — the `next_step` from `erk objective check --json-output`, or "none"

This is flat labeled text, not JSON. The format is optimized for haiku-tier agents to produce reliably without JSON serialization errors. Roadmap step statuses use the same values as the parser: `pending`, `done`, `in_progress`, `blocked`, `skipped`.

## Status Inference: The Cross-Cutting Concern

Roadmap step status is inferred from two signals — the explicit status column and the PR column — and this inference logic must stay consistent across all consumers.

<!-- Source: src/erk/cli/commands/exec/scripts/objective_roadmap_shared.py, parse_roadmap -->

The canonical status inference lives in `parse_roadmap()` in `objective_roadmap_shared.py`. The priority order:

1. **Explicit status column** — `done`, `blocked`, `skipped`, `in-progress`, `pending` are used directly
2. **Column fallback** — if status is ambiguous, a `#NNN` in the PR column infers `done`, and a `#NNN` in the Plan column infers `in_progress`
3. **Default** — `pending` when neither signal is present

This same logic is described in prose in the `objective-next-plan.md` command prompt (Step 2, status mapping section). When modifying status inference, both locations must be updated.

**Why PR-column inference exists:** Legacy objective issues often had PR links in the PR column without updating the status column. Rather than requiring retroactive cleanup, the parser infers status from the PR reference as a fallback. Explicit status always wins.

## Agent Delegation Pattern

<!-- Source: .claude/commands/erk/objective-next-plan.md -->

The `objective-next-plan` command delegates objective fetching to a haiku Task agent (Step 2) for token efficiency. The parent agent never directly parses the objective issue body — it receives a pre-structured summary from the subagent.

**Why haiku:** Objective data fetching is mechanical work (call `erk exec get-issue-body`, call `erk objective check --json-output`, format results). Haiku handles this at lower token cost without sacrificing reliability.

**Why a subagent at all:** Without delegation, the parent agent would spend context window tokens on the full objective issue body (often thousands of tokens of roadmap tables and implementation context). The subagent compresses this to just the fields the parent needs for step selection.

## Validation and the Check Command

<!-- Source: src/erk/cli/commands/objective/check_cmd.py, validate_objective -->

`erk objective check` validates roadmap consistency through five checks: label presence, roadmap parsing, status/PR consistency, orphaned done-without-PR steps, and sequential phase numbering. The `--json-output` flag exposes full parsed phases and summary statistics.

<!-- Source: .claude/commands/local/objective-view.md -->

The `objective-view` command uses a separate analysis path — it passes the raw objective body to haiku for phase progress analysis rather than calling `erk objective check`. This works because `objective-view` only needs aggregate progress (steps done per phase), not the full validation.

## Related Documentation

- [Token Optimization Patterns](../planning/token-optimization-patterns.md) — Task agent delegation pattern
- [Objective Commands](../cli/objective-commands.md) — CLI commands that consume these formats
- Objective format templates live in `.claude/skills/objective/references/format.md` (loaded via the `objective` skill)
