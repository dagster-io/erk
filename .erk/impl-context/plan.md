# Documentation Plan: Split tests/tui/test_app.py into tests/tui/app/ sub-module

## Context

This plan captures documentation opportunities from PR #8336, which split a 3,802-line test file (`tests/tui/test_app.py`) into a well-organized 13-file subdirectory (`tests/tui/app/`). The refactor moved 33 test classes and 141 tests without modifying any behavior — a pure mechanical reorganization following established patterns in the codebase.

Future agents will benefit from understanding when and how to perform this type of test file split. The project recommends ~500 lines per test file, but this file grew to 6-8x that threshold before being addressed. Documenting the decision criteria, mechanical process, and verification checklist will help agents proactively split test files before they become unwieldy.

The PR also surfaced coordination issues between automated review bots, which flagged valid patterns (Fake test helper default parameters) as violations before self-correcting. Clarifying these exceptions will prevent recurring false positive confusion.

## Raw Materials

PR #8336: Split tests/tui/test_app.py into tests/tui/app/ sub-module

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 8     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. Test File Organization Pattern

**Location:** `docs/learned/testing/test-file-organization.md`
**Action:** CREATE
**Source:** [PR #8336]

**Draft Content:**

```markdown
# Test File Organization

This document describes when and how to split large test files into subdirectories.

## read-when

- Creating a new test file that might exceed 500 lines
- Working with a test file approaching 1,000+ lines
- Refactoring test modules for maintainability

## Decision Threshold

Split test files when they reach:
- **Recommended threshold:** ~500 lines
- **Mandatory split:** 1,000+ lines OR 10+ test classes

## Mechanical Refactor Process

1. **Analyze the existing file** — Count classes, identify logical groupings
2. **Plan the split** — Map each class to a target file based on functional area
3. **Create the subdirectory** — Add `__init__.py` and target test files
4. **Move classes verbatim** — Preserve imports, docstrings, and all test logic
5. **Update imports** — Ensure all moved tests can find their dependencies
6. **Delete the original file** — Remove once all content is migrated

## Verification Checklist

- [ ] Test count preserved (run `pytest --collect-only` before and after)
- [ ] All tests pass (or same failures as before)
- [ ] Linting clean (`ruff check`)
- [ ] Type checking clean (`ty check`)
- [ ] Original file deleted

## Examples

See `tests/tui/app/` subdirectory structure (13 files from PR #8336).
See `tests/unit/cli/commands/pr/submit_pipeline/` for another example (12 files).

## Related Documentation

See docs/learned/testing/submit-pipeline-tests.md for the submit-pipeline split precedent.
```

---

#### 2. Fake Class Parameter Exemption Documentation

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8336]

**Draft Content:**

Add to the tripwires file:

```markdown
## Known Review Bot False Positives

### Fake Class Default Parameters

**Trigger:** Review bots flag default parameter values in Fake test helper classes

**False positive:** Fake test helper classes are explicitly exempt from the "no default parameter values" rule per api-design.md line 61.

**Rationale:** Fake classes need optional configuration parameters for setting up different test scenarios. For example, `_FakePopen` accepts optional `returncode`, `stdout`, and `stderr` parameters to configure subprocess behavior in tests.

**Action:** Dismiss bot comments flagging default parameters in classes named `Fake*` or `_Fake*`.
```

---

#### 3. Test File Size Tripwire

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [PR #8336]

**Draft Content:**

Add to the tripwires file:

```markdown
## Test File Size

**Before:** Creating or modifying test files with 500+ lines or 10+ test classes

**Warning:** Consider splitting into subdirectory by functional area. Threshold: ~500 lines recommended, mandatory split at 1,000+ lines or 10+ test classes.

**Reference:** See `tests/tui/app/` refactor (PR #8336) and docs/learned/testing/test-file-organization.md for the complete pattern.
```

---

### MEDIUM Priority

#### 4. Review Bot Architecture

**Location:** `docs/learned/ci/review-bot-architecture.md`
**Action:** CREATE
**Source:** [PR #8336]

**Draft Content:**

```markdown
# Review Bot Architecture

This document describes the automated review bots that run on PRs and their responsibilities.

## read-when

- Understanding why multiple bots commented on the same issue
- Debugging bot behavior or false positives
- Adding new review bot capabilities

## Active Review Bots

| Bot | Responsibilities |
|-----|------------------|
| test-coverage-review | Validates test coverage for new code |
| dignified-code-simplifier-review | Suggests code simplifications |
| dignified-python-review | Enforces Python coding standards |
| tripwires-review | Checks for tripwire violations |

## Defense in Depth vs Duplication

Multiple bots may flag the same issue. This is intentional defense in depth — catching violations through multiple lenses increases reliability. However, when one bot dismisses its own comment, other bots should respect that dismissal.

## Bot Self-Correction

Bots can post follow-up comments dismissing their own false positives. When you see a bot comment followed by a dismissal from the same bot, the dismissal takes precedence.

## Related Documentation

See docs/learned/testing/tripwires.md for known false positive patterns.
```

---

#### 5. Plan-Driven PR Artifacts

**Location:** `docs/learned/planning/plan-pr-artifacts.md`
**Action:** CREATE
**Source:** [PR #8336]

**Draft Content:**

```markdown
# Plan-Driven PR Artifacts

This document explains the `.impl/` directory structure in plan-driven PRs.

## read-when

- Reviewing a PR with `.impl/` directory
- Understanding erk's planning workflow artifacts
- Confused about `.impl/` files in a PR

## Expected Files

Plan-driven PRs include these artifacts:

| File | Purpose |
|------|---------|
| `.impl/impl-context/plan.md` | The implementation plan that guided this PR |
| `.impl/impl-context/ref.json` | Plan metadata (issue number, worktree info) |
| `.impl/run-info.json` | Execution metadata (timestamps, agent info) |

## Why These Files Exist

These files are **expected and normal** in erk's plan-driven workflow. They document the plan that was implemented, enabling traceability from PR back to the original plan issue.

## Reviewing Plan-Driven PRs

When reviewing, you can:
1. Read `plan.md` to understand the implementation strategy
2. Compare the actual changes against the plan
3. Verify the implementation followed the documented approach

These files do not need review — they are artifacts, not implementation code.
```

---

#### 6. Post-Implementation Reference Updates

**Location:** Multiple files
**Action:** UPDATE_REFERENCES
**Source:** [PR #8336]

**Draft Content:**

After the test_app.py split is merged, update these files:

1. **`docs/learned/testing/tui-subprocess-testing.md`**
   - Update `_FakePopen` location from `tests/tui/test_app.py` to `tests/tui/app/test_async_operations.py`
   - Update any test_app.py example references to point to new subdirectory files

2. **`docs/learned/textual/testing.md`**
   - Update test example references from `tests/tui/test_app.py` to appropriate files in `tests/tui/app/`

---

### LOW Priority

#### 7. Preview-Before-Action Command Pattern

**Location:** `docs/learned/commands/preview-action-pattern.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# Preview-Before-Action Command Pattern

This document describes the pattern of read-only preview commands paired with action commands.

## read-when

- Designing new command pairs
- Understanding pr-preview-address / pr-address relationship
- Implementing safe-by-default command UX

## Pattern Description

Some commands come in preview/action pairs:
- **Preview command:** Shows what would happen without making changes
- **Action command:** Performs the actual operation

Both commands share the same underlying analysis logic, ensuring the preview accurately reflects what the action will do.

## Example: PR Address Commands

- `/erk:pr-preview-address` — Shows classified feedback and planned actions (read-only)
- `/erk:pr-address` — Classifies feedback and executes resolution actions

Both use the `pr-feedback-classifier` skill for analysis.

## Benefits

- User can review the plan before committing
- Same analysis code path ensures accuracy
- Reduces risk of unexpected changes
```

---

#### 8. Skill Context Metadata Investigation

**Location:** `docs/learned/commands/` or investigation note
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

This is an investigation item, not a documentation item. The session revealed a tension:

**Command docs state:** Use Task tool (NOT skill invocation) because `context: fork` metadata does not create true subagent isolation in `--print` mode.

**Observed behavior:** Agent used Skill tool invocation successfully.

**Investigation needed:**
1. Test whether `context: fork` in skill metadata provides true subagent isolation
2. Determine if the Task tool recommendation is overly cautious
3. Update pr-address command guidance based on findings

This does not need documentation until the investigation is complete.

---

## Contradiction Resolutions

**No contradictions detected.** Existing documentation is internally consistent:
- Submit pipeline pattern advocates for splitting large test files (supports this plan)
- Test organization docs show precedent for creating test subdirectories (aligns with this plan)
- No docs suggest keeping large test files together

---

## Stale Documentation Cleanup

**No stale documentation detected.** All verified references exist and are accurate.

**Post-implementation updates required:** After the test_app.py split is merged, reference updates are needed (see item #6 above). These are not stale now — they will become stale after the merge.

---

## Prevention Insights

### 1. Review Bot False Positive Noise

**What happened:** Multiple review bots flagged Fake class default parameters as violations, then had to self-correct with dismissal comments.

**Root cause:** The exception for Fake classes (api-design.md line 61) is not sufficiently visible to bot heuristics or reviewers.

**Prevention:** Document the Fake class exemption prominently in testing tripwires as a "Known False Positive" section.

**Recommendation:** ADD_TO_DOC (see item #2)

---

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Test File Size Threshold

**Score:** 5/10 (criteria: Non-obvious +2, Cross-cutting +2, Repeated pattern +1)

**Trigger:** Before creating test file with 500+ lines or 10+ test classes

**Warning:** Consider splitting into subdirectory by functional area. See `tests/tui/app/` refactor (PR #8336) as reference pattern. Threshold: ~500 lines recommended, mandatory split at 1,000+ lines or 10+ test classes.

**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because file size thresholds are subjective and not enforced by tooling. Without a documented tripwire, test files silently grow to unmaintainable sizes. The submit-pipeline tests were split previously, and now TUI tests were split — this repeated pattern validates the need for proactive guidance. The tripwire applies across all test directories, making it a cross-cutting concern.

---

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Fake Class Parameter Exemption

**Score:** 3/10 (criteria: Cross-cutting +2, External tool quirk +1)

**Notes:** This is a false positive pattern rather than a code error pattern. The harm is noise from bot comments, not code bugs. Documenting as a "Known False Positive" section in tripwires is more appropriate than a traditional tripwire warning. May warrant promotion if bot false positives continue to cause confusion in future PRs.
