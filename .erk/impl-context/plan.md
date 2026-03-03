# Plan: Add Phase 0 Plan-Only PR Detection to pr-address

## Context

When `/erk:pr-address` is invoked on a plan-only PR (where the diff is just `.erk/impl-context/plan.md`), two failure modes occur:

1. **In plan mode**: Creates a "plan to edit the plan" (meta-planning) — confusing and useless
2. **Not in plan mode**: Edits the plan AND tries to execute the plan's described changes — too broad

The root cause is that pr-address has no detection for plan-only PRs. It only distinguishes Code Review Mode (default) vs Plan Review Mode (`erk-plan-review` label). Plan-only PRs fall through to Code Review Mode.

## Changes

### 1. Add Phase 0 to `.claude/commands/erk/pr-address.md`

Insert a new **Phase 0: Mode Detection** section before the current Phase 1. This section:

1. Checks for `erk-plan-review` label → existing Plan Review Mode (unchanged)
2. **NEW**: Checks if `.erk/impl-context/plan.md` is git-tracked → Plan File Mode
3. Neither → Code Review Mode (existing behavior, Phases 1-6)

Detection command:
```bash
git ls-files --error-unmatch .erk/impl-context/plan.md >/dev/null 2>&1
```

Also add a note at the top of the Agent Instructions section:

> **Plan mode**: If plan mode is active, exit it first (press `Escape`). This command manages its own execution flow and needs to make edits directly.

### 2. Add Plan File Mode section to `.claude/commands/erk/pr-address.md`

Add a new section after the Agent Instructions header (before current Phase 1) that describes the Plan File Mode workflow. This is a **complete alternative flow** — when active, Phases 1-6 are skipped entirely.

**Plan File Mode workflow:**

1. **Classify feedback** — same Task-based classifier as Phase 1
2. **Display plan** — same as Phase 2
3. **Execute by batch** — same structure as Phase 3, but with these constraints:
   - **ONLY edit `.erk/impl-context/plan.md`** (and `ref.json` if relevant)
   - **Interpret all feedback as "modify the plan text"** — NEVER execute changes the plan describes
   - Explicitly: if the reviewer says "add a step to do X", add text to the plan describing step X. Do NOT actually do X.
   - Use `git add -f .erk/impl-context/plan.md` for commits (directory is gitignored)
4. **Resolve threads** — same as Phase 4
5. **Push** — `git push` directly (plan PRs don't use graphite submit)
6. **Skip** update-pr-description and upload-impl-session (plan PRs have their own formatting)

The key behavioral constraint to emphasize:

> **CRITICAL**: In Plan File Mode, you are editing a *document* — the plan. When a reviewer says "make the language about X more emphatic" or "add a step for Y", you modify the plan *text*. You do NOT make changes to any files described in the plan.

### 3. Update `docs/learned/erk/pr-address-workflows.md`

Add a new section documenting Plan File Mode alongside the existing Plan Review Mode section. Explain:
- How it's triggered (git-tracked `.erk/impl-context/plan.md`)
- How it differs from Plan Review Mode (different file target, no issue sync)
- The behavioral constraint about not executing plan steps

### 4. Update `docs/learned/architecture/phase-zero-detection-pattern.md`

Add plan-only PR detection as a second example in the "Pattern in Practice: pr-address" section, showing file-based detection alongside the existing label-based detection.

## Verification

1. Read the modified pr-address.md to confirm the Phase 0 detection and Plan File Mode section are coherent
2. Checkout a plan-only PR branch, confirm `.erk/impl-context/plan.md` is git-tracked
3. Run `/erk:pr-address` and verify it enters Plan File Mode
4. Confirm it only edits plan.md, not files described in the plan
