# Documentation Plan: Fix CI label check - plan-review to erk-plan-review

## Context

This implementation fixed a critical mismatch between the Python constant `PLAN_REVIEW_LABEL = "erk-plan-review"` (defined in `src/erk/cli/constants.py:52`) and hardcoded label values of `"plan-review"` that appeared throughout the CI workflow files. The mismatch caused plan review PRs to not be properly identified for CI skipping, as the workflows were checking for the wrong label name.

Understanding this fix matters for future developers because CI label-based gating is a silent failure mode: when a label name doesn't match, no errors are thrown—the workflow simply evaluates the wrong conditional logic. This PR demonstrates that label names used in CI automation must be synchronized across multiple locations: job conditions, step names, and documentation examples. The fix itself was straightforward, but the fact that this inconsistency existed at all points to a gap in our documentation around CI label management.

The key insight from this implementation is that when Python constants define authoritative values (like `PLAN_REVIEW_LABEL`), those constants cannot be directly interpolated into YAML workflow files. This creates a synchronization challenge that must be managed through documentation discipline and potentially automation.

## Raw Materials

https://gist.github.com/schrockn/360bba2641f8f9619929d5248d5f521a

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 6     |
| Contradictions to resolve      | 1     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Workflow Gating Patterns Documentation

**Location:** `docs/learned/ci/workflow-gating-patterns.md`
**Action:** UPDATE
**Source:** [PR #6400]

**Changes Required:**

Update all examples showing the old label name `'plan-review'` to `'erk-plan-review'`:
- Core pattern examples
- WRONG vs CORRECT pattern sections
- Safe defaults section
- Combined conditions examples
- Job conditions examples
- Autofix safety patterns
- Decision tables

#### 2. GitHub Actions Label Queries Documentation

**Location:** `docs/learned/ci/github-actions-label-queries.md`
**Action:** UPDATE
**Source:** [PR #6400]

**Changes Required:**

Update label references in implementation pattern examples:
- Job condition examples: change `'plan-review'` to `'erk-plan-review'`
- Grep check examples: change `'plan-review'` to `'erk-plan-review'`
- Skip conditions lists: change `'plan-review'` to `'erk-plan-review'`

#### 3. PR Address Command Documentation

**Location:** `.claude/commands/erk/pr-address.md`
**Action:** UPDATE
**Source:** [PR #6400]

**Changes Required:**

Update the Phase 0 detection section to use the correct label name `erk-plan-review` instead of `plan-review`. The detection mechanism remains the same—only the literal string changes.

#### 4. CI Label Rename Checklist (NEW - Tripwire)

**Location:** `docs/learned/ci/label-rename-checklist.md`
**Action:** CREATE
**Type:** Tripwire documentation
**Score:** 6/10

**Purpose:** Document the comprehensive checklist for renaming GitHub labels used in CI automation, ensuring all references across Python constants, workflow files, and documentation are synchronized.

**Key Sections:**
- Source of truth verification (Python constants)
- GitHub Actions workflows search and update
- Documentation updates across all guides and commands
- Verification steps (grep for old names, test PR)
- Why this matters (silent failure modes)

### MEDIUM Priority

#### 5. PR Address Workflows Documentation

**Location:** `docs/learned/erk/pr-address-workflows.md`
**Action:** UPDATE
**Source:** [PR #6400]

**Changes Required:**

Update the Plan Review Mode section to use `erk-plan-review` instead of `plan-review` in all label references and descriptions.

#### 6. GitHub Actions Label Filtering Reference (NEW)

**Location:** `docs/learned/ci/github-actions-label-filtering.md`
**Action:** CREATE
**Type:** Reference documentation

**Purpose:** Provide a quick reference for the GitHub Actions label filtering pattern, explaining the `.*.name` syntax, negation semantics, and how to keep workflow label strings synchronized with Python constant definitions.

**Key Sections:**
- Core pattern explanation with syntax breakdown
- Why negation matters for safe defaults
- Authoritative label definitions (reference to Python constants)
- Link to CI Label Rename Checklist

## Contradiction Resolutions

### 1. Label Name Inconsistency Across Codebase

**Problem:** Multiple documentation files contained examples showing `'plan-review'` while the Python constant `PLAN_REVIEW_LABEL = "erk-plan-review"` defined the authoritative label.

**Root Cause:** YAML workflow files cannot interpolate Python constants, so hardcoded label strings must be manually kept in sync. No automation existed to detect drift.

**Resolution:** Update all documentation examples to `'erk-plan-review'` to match the corrected CI workflows. The constant was always correct—only the workflows and documentation were out of sync.

**Impact:** Ensures future developers see consistent, accurate examples of label usage throughout the codebase.

## Prevention Insights

### 1. Incomplete Label Rename Pattern

**What happened:** Label renamed in Python constant but not in workflow YAML files.

**Root cause:** YAML can't interpolate constants; manual synchronization required.

**Prevention Strategy:** CI Label Rename Checklist (HIGH priority documentation item) documenting all locations that must be updated. Consider adding a CI check that validates workflow label strings against constant definitions.

**Severity:** MEDIUM - Silent failure, no runtime errors to alert developers.

### 2. Silent CI Failure Mode

**What happened:** Plan review PRs not skipped during CI because label check looked for wrong name.

**Root cause:** GitHub Actions label checks are boolean expressions that don't throw errors—they just evaluate to false.

**Prevention Strategy:** Document this failure mode in CI documentation. When debugging "CI didn't skip," always verify label names match exactly.

**Severity:** MEDIUM - Can cause incorrect CI behavior without obvious indicators.

## Tripwire Candidates

### CI Label Rename Impact (APPROVED TRIPWIRE)

**Score:** 6/10
**Trigger:** Before renaming a GitHub label used in CI automation

**Warning Message:**
"Labels are referenced in multiple places: (1) Job-level `if:` conditions in all workflow files, (2) Step name descriptions and comments, (3) Documentation examples showing the label check. Missing any location will cause CI behavior to diverge from intent. Use the CI Label Rename Checklist to ensure comprehensive updates."

**Why it's a tripwire:**
- **Non-obvious (+2)**: Developers may update the Python constant and assume they're done, not realizing YAML files need manual updates
- **Cross-cutting (+2)**: Spans multiple workflow files, multiple locations within each file, plus documentation
- **Destructive potential (+2)**: Silent failure mode—no runtime errors, just different CI behavior

## Potential Tripwires (Score 2-3)

### GitHub Actions Label Filtering Syntax Pattern

**Score:** 3/10
**Notes:** The `.*.name` syntax for extracting label names is specific to GitHub Actions and not immediately obvious. Already documented in existing `github-actions-label-queries.md`. Monitor for repeated confusion; could be promoted to tripwire if it becomes a pattern.

### Hardcoded Label Strings in Workflow Files

**Score:** 3/10
**Notes:** The pattern of hardcoded label strings diverging from Python constants is a repeated risk. This PR fixes one instance; similar inconsistencies could arise with other labels. Worth monitoring; consider adding a CI check that validates workflow label strings against constant definitions.