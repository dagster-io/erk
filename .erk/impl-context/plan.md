# Remove All `erk-plan-review` Label References

## Context

The `erk-plan-review` GitHub label was previously used to:
1. Gate CI workflows (skip CI on plan-review PRs)
2. Trigger "Plan Review Mode" in `/erk:pr-address` (alternative flow editing `PLAN-REVIEW-*.md` files)

We no longer use this label or treat it specially. All references must be eliminated.

Note: `erkweb/src/client/components/PlanReviewPanel.tsx` is a **separate feature** (web UI for annotating local plans) and should NOT be touched.

## Files to Change

### 1. GitHub Workflows (functional)

**`.github/workflows/ci.yml`** — Remove label gating from 3 job conditions:
- Line 19: `check-submission` — remove `&& !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')`
- Line 31: `no-impl-context` — same removal
- Line 213: `ci-summarize` — same removal

**`.github/workflows/code-reviews.yml`**:
- Line 13: `discover` job — same removal

### 2. Command: `.claude/commands/erk/pr-address.md`

In **Phase 0: Mode Detection**, remove step 1 entirely (the plan-review label check and "If found → Plan Review Mode"):

Remove:
```
1. **Check for `erk-plan-review` label**:
   ```bash
   gh pr view --json labels -q '.labels[].name' | grep -q '^erk-plan-review$'
   ```
   If found → **Plan Review Mode** (existing behavior, see Plan Review Mode section in pr-address-workflows docs)

2. **Check if `.erk/impl-context/plan.md` is git-tracked**:
```

Replace with (renumbered):
```
1. **Check if `.erk/impl-context/plan.md` is git-tracked**:
```

The "Plan Review Mode" section referenced in this command lives in the docs (pr-address-workflows.md) — it will be removed there as well.

### 3. Test: `tests/unit/cli/commands/exec/scripts/test_get_pr_view.py`

In `test_get_pr_view_labels`, remove `erk-plan-review` from the test labels:
- Line 163: `labels=("erk-pr", "erk-plan-review", "bug")` → `labels=("erk-pr", "bug")`
- Line 176: `assert output["labels"] == ["erk-pr", "erk-plan-review", "bug"]` → `assert output["labels"] == ["erk-pr", "bug"]`

### 4. Docs: `docs/learned/erk/pr-address-workflows.md`

Remove the entire **Plan Review Mode** section (lines 57-103): the `### Plan Review Mode` heading through the link to `PR-Based Plan Review Workflow`.

Update the **Plan File Mode** section's comparison table (currently compares against Plan Review Mode) to remove that column or simplify.

### 5. Docs: `docs/learned/architecture/phase-zero-detection-pattern.md`

Update the "Pattern in Practice: pr-address" section (lines 48-73):
- Remove step 1 (label-based detection) from the cascade
- Update the cascade description to 2 steps: file-based → default
- Remove "Label-Based: Plan Review Mode" subsection
- Remove the mention of "ordered cascade" priority logic

### 6. Docs: `docs/learned/ci/workflow-gating-patterns.md`

Update to remove `erk-plan-review`-specific content:
- Remove/rewrite the "Negation Pattern" section which is entirely about plan-review label gating
- Remove "Combining Draft and Label Checks" section (specific to the plan-review pattern)
- Keep any general patterns that remain applicable (branches-ignore, paths-ignore patterns)

### 7. Remaining CI docs (minor updates)

These docs have secondary/example references to `erk-plan-review`. Update each to remove references:
- `docs/learned/ci/job-ordering-strategy.md` — remove mention of check-submission skipping plan-review PRs
- `docs/learned/ci/github-actions-label-filtering.md` — remove plan-review examples
- `docs/learned/ci/github-actions-label-queries.md` — remove plan-review examples
- `docs/learned/ci/label-rename-checklist.md` — remove PLAN_REVIEW_LABEL references
- `docs/learned/ci/ci-failure-summarization.md` — remove plan-review skip mention
- `docs/learned/testing/fake-github-mutation-tracking.md` — remove plan-review from example assertion

## Verification

1. Run `grep -r "plan-review\|plan_review\|PLAN_REVIEW" .github/ .claude/commands/ tests/ docs/ src/` — expect zero matches (excluding git history and `erkweb/`)
2. Run unit tests for the modified test file:
   ```
   uv run pytest tests/unit/cli/commands/exec/scripts/test_get_pr_view.py
   ```
3. Validate CI YAML syntax (can be checked via `act --dryrun` or pushing to a branch)
