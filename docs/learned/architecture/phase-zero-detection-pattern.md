---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - implementing mode variants in multi-phase commands
  - designing conditional execution workflows
  - debugging scattered mode detection logic
title: Phase 0 Detection Pattern
tripwires:
  - action: Detect mode in Phase 0 before any other phases execute
    score: 5
last_audited: "2026-02-08"
audit_result: clean
---

# Phase 0 Detection Pattern

## Why Phase 0 Exists

Multi-phase commands often support fundamentally different operational modes (code review vs plan review, interactive vs batch, local vs remote). **The timing of mode detection determines code clarity**: detect early and branch cleanly, or detect late and scatter `if mode == X` checks across every phase.

Phase 0 detection solves this by **deciding the execution path before any work begins**, preventing wasted effort and keeping mode-specific logic consolidated.

## The Core Problem

Without upfront detection, commands suffer from:

1. **Starting in the wrong mode** — begin Phase 1 work, discover incorrect mode in Phase 2, backtrack
2. **Scattered conditionals** — every phase checks `if mode == X`, duplicating logic
3. **Unclear execution flow** — difficult to understand which code runs in which mode
4. **Wasted computation** — execute phases irrelevant to the current mode

The symptom: "Wait, this is plan review mode? But I already classified the feedback as code comments..."

## The Solution: Detect Before Execute

Add **Phase 0** as the first step:

1. **Detect mode** based on context (labels, flags, files, environment)
2. **Branch the entire flow** — mode-specific paths become separate sections
3. **Skip irrelevant phases** — only run phases that apply to the detected mode

This creates a decision tree at the entry point rather than conditionals scattered throughout.

## Pattern in Practice: pr-address

<!-- Source: .claude/commands/erk/pr-address.md, Phase 0 section -->

The `/erk:pr-address` command handles two distinct modes:

- **Code review mode**: Address code review feedback (Phases 1-4)
- **Plan review mode**: Address plan document feedback (separate flow)

Phase 0 determines which path to follow by checking for the `erk-plan-review` label on the PR. If the label exists, the command skips normal Phases 1-4 entirely and enters a separate plan review flow that edits `PLAN-REVIEW-{issue}.md` instead of source code.

See Phase 0 implementation in `.claude/commands/erk/pr-address.md` (lines 32-50).

### Why This Works

**Single decision point**: Mode logic lives in Phase 0. Phases 1-4 don't check the mode — they simply don't run if plan review mode is active.

**Complete separation**: The command document has distinct sections:

- Phase 0: Detection logic
- Phases 1-4: Code review mode (standard flow)
- Separate section: Plan review mode (alternative flow)

Anyone reading the command knows exactly which phases run in which mode without tracking conditionals.

**No mode leakage**: Code review phases never see plan review context. Plan review phases never see code review logic.

## Detection Mechanisms

### Label-Based Detection

Check for a PR label to determine mode:

```bash
gh pr view --json labels -q '.labels[].name'
```

If the label exists in the output, switch to alternative mode.

<!-- Source: src/erk/cli/constants.py:52 -->

Example: The `PLAN_REVIEW_LABEL` constant defines `"erk-plan-review"` as the label that triggers plan review mode.

**Why labels work**: Labels are applied by automated workflows (e.g., `erk exec plan-create-review-pr`) and remain stable throughout the PR lifecycle. They're a durable signal of PR intent.

### Flag-Based Detection

Command-line flags provide explicit mode selection:

```bash
my-command --dry-run
```

The flag determines whether to execute mutations or just simulate them.

**Trade-off**: Flags require user knowledge. Labels are set by workflows and don't require user decision.

### Environment-Based Detection

Check environment variables:

```bash
if [ "$CI" = "true" ]; then
  # CI mode
else
  # Local mode
fi
```

**Why this works**: CI environment is a stable signal. Local vs CI often have different constraints (no interactivity in CI, different permissions).

### File-Based Detection

Check for presence/absence of files:

```bash
if [ -f ".impl/plan.md" ]; then
  # Plan implementation mode
else
  # Ad-hoc development mode
fi
```

**Trade-off**: File-based detection assumes files are stable indicators. If files can be stale or partially written, this becomes unreliable.

## When to Use Phase 0

Use Phase 0 detection when:

- **Multi-phase command**: The command has sequential phases (Phase 1, 2, 3...)
- **Mode changes fundamental behavior**: Not just a flag tweaking one step, but a different execution path
- **Multiple phases affected**: If only one phase cares about the mode, add a conditional there instead
- **Modes are mutually exclusive**: Can't be in both modes simultaneously

## When NOT to Use Phase 0

Skip Phase 0 when:

- **Single-phase command**: No phases to orchestrate, just add `if` to the one place that cares
- **Mode is additive**: Both paths execute, mode just adds extra behavior on top
- **Mode affects one phase only**: Add conditional in that phase rather than creating upfront detection
- **Modes can overlap**: Not binary — multiple modes can be active, so detection isn't clean branching

## Anti-Patterns

### WRONG: Late Detection

```markdown
### Phase 1: Classify Feedback

1. Fetch feedback
2. Parse comments
3. Check if plan review mode
4. ERROR: Should have checked this before Phase 1 started
```

**Why wrong**: Already fetched and parsed feedback assuming code review mode. Wasted work.

**Correct approach**: Phase 0 detects mode, Phase 1 only runs if code review mode is active.

### WRONG: Scattered Detection

```markdown
### Phase 1: Classify

- If plan review: classify differently

### Phase 2: Generate

- If plan review: generate differently

### Phase 3: Apply

- If plan review: apply differently
```

**Why wrong**: Mode logic duplicated across every phase. Hard to understand the two execution paths.

**Correct approach**: Phase 0 branches to separate flows. Each flow has its own Phase 1/2/3 without conditionals.

### WRONG: No Detection Until Failure

```markdown
### Phase 2: Generate Fixes

1. Try to generate code fixes
2. Realize the PR has a plan review label
3. Abort with error
```

**Why wrong**: Phase 2 is too late to discover mode. Should have detected in Phase 0 and never entered Phase 1.

**Correct approach**: Phase 0 detects label and branches to plan review flow immediately.

## Related Patterns

### Label-Driven Branching

<!-- Source: .claude/commands/erk/pr-address.md, Phase 0 detection -->

Phase 0 detection often uses GitHub PR labels as feature switches. Labels represent mode variants and are applied automatically by workflows (e.g., `erk exec plan-create-review-pr` applies `erk-plan-review` label).

**Why labels**: They're durable (don't change during PR lifecycle) and workflow-controlled (no user decision needed).

### State Machine Entry Point

Phase 0 detection is a state machine entry point:

- **State**: The detected mode (code review, plan review)
- **Transitions**: Moving through phases within that mode
- **Guards**: The detection logic determines initial state

Once the initial state is determined, transitions within that mode never cross to the other mode's transitions.

## Implementation Checklist

When adding Phase 0 detection to a command:

- [ ] Create Phase 0 section at the top of the command document
- [ ] Identify detection mechanism (label, flag, file, environment)
- [ ] Document both modes clearly (what makes them different, not just "mode A vs mode B")
- [ ] Branch entire execution flow (normal phases vs alternative mode section)
- [ ] Test both paths (ensure both modes work correctly from Phase 0 onward)
- [ ] Update command description (explain when each mode activates)

## Related Documentation

- [Workflow Gating Patterns](../ci/workflow-gating-patterns.md) — Conditional execution in CI contexts
- [PR Address Workflows](../erk/pr-address-workflows.md) — Complete pr-address workflow including both modes
- [Plan Review Workflow](../planning/pr-review-workflow.md) — The plan review mode triggered by Phase 0 detection

## Attribution

Pattern formalized during PR #6237 implementation (plan review mode for pr-address).
