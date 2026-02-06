---
title: CI Label Rename Checklist
read_when:
  - renaming a GitHub label used in CI automation
  - updating label references across the codebase
  - debugging why CI label checks aren't working after a rename
tripwires:
  - action: "Renaming a GitHub label used in CI automation"
    warning: "Labels are referenced in multiple places: (1) Job-level if: conditions in all workflow files, (2) Step name descriptions and comments, (3) Documentation examples showing the label check. Missing any location will cause CI behavior to diverge from intent. Use the CI Label Rename Checklist to ensure comprehensive updates."
    score: 6
last_audited: "2026-02-05"
audit_result: clean
---

# CI Label Rename Checklist

## Problem

When renaming a GitHub label that's used in CI automation, the change must be synchronized across multiple locations that cannot automatically detect the rename. Missing any location creates silent failures where CI behavior diverges from intent without throwing errors.

## Why This Matters

GitHub Actions label checks are boolean expressions that evaluate to true/false. When a label name doesn't match, the expression silently evaluates to false—no errors are thrown. This creates a silent failure mode where:

- PRs with the label aren't skipped as intended
- CI runs when it shouldn't (wasting resources)
- CI doesn't run when it should (missing test coverage)
- No obvious indicators point to the label mismatch

## The Challenge

Unlike code references that can be caught by static analysis, label string literals in YAML workflow files:

- Cannot be interpolated from Python constants
- Are not validated at workflow parse time
- Have no type checking or linting
- Only fail silently at runtime through incorrect boolean evaluation

## Comprehensive Checklist

When renaming a label used in CI automation, update **all** of these locations:

### 1. Source of Truth: Python Constants

**File:** `src/erk/cli/constants.py`

Verify the Python constant is updated. This is the authoritative definition:

```python
PLAN_REVIEW_LABEL = "erk-plan-review"  # Correct
```

### 2. GitHub Actions Workflows

**Pattern to search:** Grep for the old label name in `.github/workflows/`

```bash
grep -r "old-label-name" .github/workflows/
```

**Locations within workflows:**

#### Job-level conditions

```yaml
if: github.event.pull_request.draft != true && !contains(github.event.pull_request.labels.*.name, 'erk-plan-review')
```

Update all `if:` conditions that check for the label.

#### Step-level label checks

```yaml
- name: Check erk-plan-review label
  run: |
    if echo "$labels" | grep -q "erk-plan-review"; then
      echo "has_plan_review_label=true" >> $GITHUB_OUTPUT
    fi
```

Update:

- Step names that mention the label
- grep patterns checking for the label
- Comments explaining what the label does

### 3. Documentation Updates

**Pattern to search:** Grep for the old label name across docs

```bash
grep -r "old-label-name" docs/
```

**Documentation categories to check:**

#### CI Documentation

- `docs/learned/ci/workflow-gating-patterns.md` - Examples showing label checks
- `docs/learned/ci/github-actions-label-queries.md` - Label query implementation patterns
- `docs/learned/ci/github-actions-label-filtering.md` - Label filtering reference (if it exists)

#### Command Documentation

- `.claude/commands/erk/pr-address.md` - Phase 0 detection logic
- Any other commands that check for the label

#### Workflow Documentation

- `docs/learned/erk/pr-address-workflows.md` - Plan review mode documentation
- Any docs explaining when the label is applied

### 4. Verification Steps

After updating all locations:

#### Grep for the old name

```bash
# Should return NO results
grep -r "old-label-name" .github/ docs/ .claude/
```

If any results remain, those are locations you missed.

#### Test with a PR

1. Create a test PR
2. Add the renamed label
3. Verify CI behavior matches expectations (skipped/run as intended)
4. Check workflow logs to confirm label checks evaluate correctly

## Related Documentation

- [GitHub Actions Workflow Gating Patterns](workflow-gating-patterns.md) - How label checks work in CI
- [GitHub Actions Label Queries](github-actions-label-queries.md) - Step-level API query pattern for push events

## Prevention Strategy

**Future improvement:** Consider adding a CI check that validates workflow label strings against Python constant definitions. This could catch drift automatically.

## Attribution

Checklist created from patterns observed in PR #6400 (fixing `plan-review` → `erk-plan-review` mismatch).
