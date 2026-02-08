---
title: Investigation Findings Checklist
read_when:
  - "before entering Plan Mode in replan workflow"
  - "verifying context preservation in consolidated plans"
  - "creating comprehensive implementation plans from investigation findings"
last_audited: "2026-02-08"
audit_result: clean
tripwires:
  - action: "entering Plan Mode in replan or consolidation workflow"
    warning: "Complete this checklist first. Sparse plans waste downstream implementation effort and cause re-discovery of findings already in context."
---

# Investigation Findings Checklist

Verification checklist ensuring investigation context is preserved when creating implementation plans. Prevents sparse plans that force downstream agents to re-discover findings.

## The Core Problem

When agents enter Plan Mode **before** structuring investigation findings, those findings remain scattered in conversation history. The resulting plan contains placeholders ("update the docs") instead of specifics ("update `docs/learned/architecture/gateway-inventory.md` lines 45-67 to add CommandExecutor entry").

Implementing agents must then repeat the entire investigation — wasting expensive context and risking different conclusions.

## When to Use This Checklist

Use before Step 6b (Enter Plan Mode) in replan or consolidation workflows:

1. **After investigation** (Steps 4-5 complete) but **before Plan Mode**
2. **When consolidating multiple plans** (check per-plan status)
3. **Before saving any implementation plan** to GitHub

The checklist creates a **checkpoint**: findings are explicitly collected and verified before plan creation begins.

---

## Pre-Plan-Mode Verification

Complete these checks **before entering Plan Mode**.

### Investigation Status

Per source plan (if replanning/consolidating):

- [ ] **Completion percentage calculated** — e.g., "4/11 items implemented (36%)"
- [ ] **Status breakdown documented** — how many items: done, partial, not started, obsolete
- [ ] **Work-already-done identified** — PR numbers and commit hashes for completed items

### Specific Discoveries

Concrete evidence from codebase exploration:

- [ ] **File paths collected** — full paths (`docs/learned/architecture/foo.md`), not generic ("the docs")
- [ ] **Line numbers noted** — format: `foo.md:45` or `foo.md:45-67` for ranges
- [ ] **Commit hashes recorded** — format: `a1b2c3d` with description of implemented work
- [ ] **PR numbers tracked** — format: `#5432` with brief description

### Corrections Found

What the original plan(s) got wrong:

- [ ] **Non-existent files identified** — plan said to update `foo.md`, but it doesn't exist
- [ ] **Wrong file names corrected** — plan said `bar.md`, actual name is `baz.md`
- [ ] **Outdated APIs documented** — plan used old function signature, actual is X
- [ ] **Already-completed items noted** — plan item was implemented in PR #5432

### Codebase Evidence

Actual implementation details (not guessed):

- [ ] **Function names verified** — actual: `parse_session_file_path()`, not guessed: `parse_session()`
- [ ] **Class signatures documented** — actual: `class CommandExecutor(ABC, WorkspaceContext)`
- [ ] **Config values recorded** with locations — actual: `SINGLE_FILE_TOKEN_LIMIT = 20_000` at line 23
- [ ] **Data structures noted** — dataclass fields, type annotations, default values

---

## Plan Content Verification

Complete these checks **after exiting Plan Mode** to verify comprehensive plan content.

### File References

- [ ] **All files have full paths** — not "update documentation", but "update `docs/learned/sessions/preprocessing.md`"
- [ ] **No generic references** — no "the config file" or "relevant docs"

### Change Descriptions

- [ ] **Specific changes described** — not "update X", but "add entry for CommandExecutor at line 105 with ABC signature"
- [ ] **Line numbers provided** where applicable — "Line 67: Change Haiku → Sonnet"
- [ ] **Reasoning included** for changes — "Fix import paths (package renamed in PR #5432)"

### Evidence and Citations

- [ ] **Evidence provided** for each step — commit hashes, PR numbers, or file locations
- [ ] **Function names are actual**, not guessed — verified from codebase exploration
- [ ] **Constants cited with values** — not "the token limit", but "20K token limit (SINGLE_FILE_TOKEN_LIMIT)"

### Verification Criteria

- [ ] **Success criteria are testable** — can verify with grep, file inspection, or running code
- [ ] **Criteria are specific**, not vague — not "documentation is complete", but "document includes SINGLE_FILE_TOKEN_LIMIT constant with value"
- [ ] **Each step has verification** — no step lacks "how to confirm complete" criterion

### No Placeholders

- [ ] **No TODO markers** in plan — no "TODO: Add specific file path"
- [ ] **No generic summaries** instead of specifics — no "update as needed" or "fix where appropriate"
- [ ] **No reference to "findings" without including them** — not "based on investigation findings, update X", but "update X at line 45 (found outdated in investigation)"

---

## Post-Plan Review

After plan is saved to GitHub, perform final review.

### Executability Test

- [ ] **Another agent could execute** without original investigation — all necessary context is in plan
- [ ] **No re-discovery required** — file paths, function names, constants are provided
- [ ] **Decisions are documented** — why items were merged, why approach was chosen

### Evidence Preservation

- [ ] **All commit hashes are in plan** — completed work is traceable
- [ ] **All PR numbers are in plan** — shipped features are referenced
- [ ] **All file paths are in plan** — agent knows exactly what to edit

### Verification Criteria Quality

- [ ] **Can verify each step objectively** — success criteria don't require interpretation
- [ ] **Clear "done" definition** for each step — agent knows when to mark step complete

---

## Consolidation-Specific Checks

Additional checks when consolidating multiple plans.

### Overlap Analysis

- [ ] **Overlapping items identified** — which items appeared in multiple source plans
- [ ] **Merge decisions documented** — why items were combined or kept separate
- [ ] **Redundancy eliminated** — duplicate items merged into single step

### Attribution Tracking

- [ ] **Each step marked with source** — "(from #123)" or "(from #123, #456)"
- [ ] **Attribution table provided** — clear map of which plan contributed what
- [ ] **Source plan context preserved** — important details from each original plan retained

### Source Plan Analysis

- [ ] **All source plans analyzed** for status — completion percentage for each
- [ ] **Corrections per plan documented** — what each original plan got wrong
- [ ] **Work-already-done identified** per plan — which plan items are implemented, by which PR

---

## Sparse vs. Comprehensive Plans

### Red Flags (Sparse Plan)

Signs the plan lacks sufficient context:

- Generic "update X" without specifics
- No line numbers or file paths
- No evidence or citations
- Vague "complete" verification
- Placeholders or TODOs in plan
- Function names that could be guessed (e.g., "the parser function")
- No source attribution in consolidation

### Green Lights (Comprehensive Plan)

Signs the plan preserves investigation findings:

- Full file paths for every reference
- Specific changes with line numbers
- Evidence (commit hashes, PR numbers, current values)
- Testable verification criteria
- Actual function/class names with signatures
- Reasoning for changes
- Source attribution (consolidation mode)

---

## Why This Matters

### Without This Checklist

1. **Investigation findings lost** — Steps 4-5 discoveries scatter in conversation history
2. **Implementing agent repeats work** — must re-discover file paths, function names, completion status
3. **Different choices made** — without evidence, agent makes different assumptions
4. **Verification impossible** — no clear success criteria

### With This Checklist

1. **Investigation findings preserved** — all discoveries explicitly structured before Plan Mode
2. **Implementing agent executes directly** — no re-discovery needed
3. **Consistent choices** — evidence guides decisions
4. **Verification clear** — testable success criteria provided

### Cost Comparison

| Aspect                    | Sparse Plan (No Checklist)         | Comprehensive Plan (Checklist Used) |
| ------------------------- | ---------------------------------- | ----------------------------------- |
| Implementation prep       | Re-discover everything             | Execute immediately                 |
| Context burned            | 10-30K tokens for re-investigation | Minimal (findings already in plan)  |
| Risk of divergence        | High (different agent, new search) | Low (evidence constrains choices)   |
| Verification              | Subjective ("looks done")          | Objective (grep, inspect, run)      |
| Attribution (consolidate) | Lost                               | Preserved per source plan           |

---

## Quick Reference

### Must-Haves Before Plan Mode (Step 6a)

1. Investigation status (completion %)
2. Specific discoveries (files, lines, commits, PRs)
3. Corrections (what original plans got wrong)
4. Codebase evidence (actual names, signatures, values)

### Must-Haves in Plan Content (Step 6b)

1. Full file paths (no generic references)
2. Specific changes (with line numbers)
3. Evidence (commit hashes, PR numbers)
4. Testable verification criteria

### Failure Modes to Avoid

- Entering Plan Mode before completing checklist (findings lost)
- Generic file references ("the docs" instead of `docs/learned/foo.md`)
- Guessed function names (not verified from codebase)
- Vague verification ("complete" instead of "includes constant X with value Y")
- Missing evidence (no commit hashes or PR numbers for completed work)

---

## Related Documentation

- [Context Preservation in Replan](../planning/context-preservation-in-replan.md) — why this checklist exists and the sparse plan problem
- [Context Preservation Patterns](../planning/context-preservation-patterns.md) — anti-pattern vs. correct pattern examples
- [Context Preservation Prompting](../planning/context-preservation-prompting.md) — prompt structures for eliciting context
- [Replan Command](../../../.claude/commands/erk/replan.md) — canonical workflow with Steps 6a-6b
