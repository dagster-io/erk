# Documentation Plan: Indicator classification pattern and documentation drift prevention

## Context

This implementation session refactored the lifecycle indicator system in erk's TUI and desktop dash components. The core change replaced ad-hoc condition checks for the ready-to-land rocket emoji with a formal `_non_blocking` set pattern. This architectural shift moves indicator classification from procedural control flow ("if not draft and not conflicts") to declarative data structure membership ("if indicator in non_blocking set").

The sessions revealed a significant meta-insight: documentation drift is a systemic risk that requires proactive prevention. An automated review bot (github-actions[bot]) detected 13 documentation drift issues before merge, including verbatim code copies, inaccurate claims about removed features, and enumeration of set values that would drift as the code evolves. The bot's multi-round review process (first detecting stale code, then detecting overly-specific prose) demonstrates that automated review can catch not just immediate drift but future drift risk.

A future agent working on indicator logic would benefit from understanding: (1) the `_non_blocking` set pattern for extensible classification, (2) how to avoid documentation drift when documenting volatile implementation details, and (3) the PR feedback resolution workflow demonstrated in these sessions.

## Raw Materials

PR #7974

## Summary

| Metric | Count |
|--------|-------|
| Documentation items | 12 |
| Contradictions to resolve | 0 |
| Tripwire candidates (score>=4) | 3 |
| Potential tripwires (score 2-3) | 2 |

## Documentation Items

### HIGH Priority

#### 1. Bot-Driven Documentation Audit Workflow

**Location:** `docs/learned/review/automated-doc-review.md`
**Action:** CREATE
**Source:** [PR #7974]

**Draft Content:**

```markdown
---
read-when:
  - receiving review feedback from github-actions bot
  - understanding automated PR documentation audits
  - addressing documentation drift warnings
tripwires: 1
---

# Automated Documentation Review

The `github-actions[bot]` automated reviewer audits PR documentation for drift risks.

## What the Bot Detects

The bot scans PR diffs and comments on documentation issues:

1. **Verbatim code copies** - Source code embedded in markdown that differs from current implementation
2. **Inaccurate claims** - Documentation referencing removed or changed features
3. **Line number fragility** - Source pointers using line numbers that will shift
4. **Enumeration drift risk** - Listing specific collection members that will change
5. **Off-diff inaccuracies** - Pre-existing issues in files touched by the PR

## Interpreting Bot Feedback

Bot comments distinguish two categories:

- **Immediate drift**: Documentation is already stale (fix required)
- **Future drift risk**: Documentation is technically accurate but fragile (refactor recommended)

## Iteration Expectations

Automated reviewers may run multiple times. After addressing first-round feedback, expect follow-up rounds detecting different levels of issues. PR #7974 required two rounds: first for stale verbatim code, second for overly-specific prose enumerating set members.

## Known Limitations

The bot can detect off-diff inaccuracies but cannot add inline comments to unchanged lines. These appear as general PR comments describing the file and issue.

## Case Study

PR #7974 caught 13 issues before merge:
- 3 verbatim code copies
- 3 inaccurate claims about removed features
- 2 line-number fragility warnings
- 2 enumeration drift risks
- 3 off-diff pre-existing inaccuracies
```

---

#### 2. Indicator Classification Set Pattern

**Location:** `docs/learned/architecture/indicator-classification-pattern.md`
**Action:** CREATE
**Source:** [PR #7974]

**Draft Content:**

```markdown
---
read-when:
  - adding new lifecycle indicators
  - modifying ready-to-land rocket logic
  - working with indicator classification
tripwires: 2
---

# Indicator Classification Pattern

Use whitelist sets for extensible indicator classification instead of individual condition checks.

## Pattern

Define classification as data, not control flow:

```python
# Instead of:
if not is_draft and not has_conflicts and review_decision != "CHANGES_REQUESTED":
    show_rocket()

# Use:
_non_blocking = {"indicator_a", "indicator_b", "indicator_c"}
if all(i in _non_blocking for i in indicators):
    show_rocket()
```

## Benefits

1. **Single source of truth** - Classification lives in one data structure
2. **Extensible** - Adding indicators doesn't require logic changes
3. **Self-documenting** - Set membership expresses business rules
4. **Maintainable** - New informational indicator = add to set; new blocking indicator = just add to indicators list

## Implementation

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`, `_build_indicators()` function for the canonical implementation.

## When to Apply

Use this pattern when:
- Classification into categories determines behavior
- Categories are stable but members may grow
- Logic currently checks multiple individual conditions

Do NOT document specific set members in learned docs - the set contents are implementation details that change. Reference the set generically.
```

---

#### 3. Documentation Drift Prevention Tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7974]

**Draft Content:**

Add to the tripwires file:

```markdown
## Verbatim Code Embedding

**Trigger:** Before embedding exact source code in markdown documentation
**Warning:** Use prose + source pointer instead. Verbatim code creates drift risk when source changes. Bot detected 3 instances in PR #7974. See `docs/learned/documentation/source-pointers.md` for patterns.
**Score:** 6 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +1)
```

---

#### 4. Enumerated Set Member Drift Tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7974]

**Draft Content:**

Add to the tripwires file:

```markdown
## Collection Member Enumeration

**Trigger:** Before enumerating specific values from a set/list/enum that may grow
**Warning:** Reference the data structure generically (e.g., "the `_non_blocking` set") instead of listing members (e.g., "pancake, eyes, checkmark"). Exception: API constants where enumeration IS the documentation. See PR #7974 bot feedback.
**Score:** 6 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
```

---

#### 5. Line Number Source Pointer Tripwire

**Location:** `docs/learned/documentation/tripwires.md`
**Action:** UPDATE
**Source:** [PR #7974]

**Draft Content:**

Add to the tripwires file:

```markdown
## Line Number Source Pointers

**Trigger:** Before using line numbers in source pointers (e.g., `file.py:42-55`)
**Warning:** ALWAYS prefer name-based identifiers (function/class names) over line numbers. Line-based pointers are fragile and shift with code changes. Use format: `file.py, function_name()`. See `docs/learned/documentation/source-pointers.md`.
**Score:** 5 (Non-obvious +2, Cross-cutting +2, Silent failure +1)
```

---

### MEDIUM Priority

#### 6. PR Feedback Resolution Workflow

**Location:** `docs/learned/pr-operations/feedback-resolution-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - addressing PR review feedback
  - running /erk:pr-address workflow
  - resolving multiple review threads
tripwires: 1
---

# PR Feedback Resolution Workflow

Complete workflow for addressing PR review feedback systematically.

## Workflow Steps

1. **Preview** - Run `/erk:pr-preview-address` to see pending feedback
2. **Classify** - Agent uses Task tool to invoke `pr-feedback-classifier` skill
3. **Batch** - Group by complexity (single-file fixes auto-proceed)
4. **Execute** - Read context, make edits, create commit
5. **Resolve** - Batch resolve threads with `erk exec resolve-review-threads`
6. **Verify** - Re-run classifier to confirm all threads resolved
7. **Update** - Run `erk exec update-pr-description` to refresh PR metadata

## Batch Thread Resolution

Use JSON stdin for efficiency when resolving multiple threads:

```bash
echo '[{"thread_id": "123", "action": "resolve"}, {"thread_id": "456", "action": "resolve"}]' | erk exec resolve-review-threads
```

## Verification Loop

After resolving threads, ALWAYS re-run the classifier before considering work complete. Automated reviewers may detect additional issues in modified files.
```

---

#### 7. Iterative PR Addressing

**Location:** `docs/learned/pr-operations/iterative-addressing.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when:
  - expecting multiple rounds of PR review
  - understanding automated reviewer behavior
  - addressing second-order feedback
tripwires: 0
---

# Iterative PR Addressing

Automated reviewers may run multiple times, each detecting different levels of issues.

## Feedback Levels

1. **First-order drift** - Stale verbatim code, incorrect facts
2. **Second-order drift** - Overly specific prose that will drift (e.g., enumerating set members)

## Expectation Setting

When working with automated review bots:
- Expect 2-3 rounds of feedback for documentation-heavy PRs
- First round catches immediate issues
- Subsequent rounds catch fragility and drift risk
- This is normal and expected, not a failure

## Strategy

1. Address all immediate issues first
2. Push and wait for next review round
3. Address fragility warnings
4. Repeat until bot is satisfied

PR #7974 required two rounds: stale code (round 1) then overly-specific prose (round 2).
```

---

#### 8. Stacked PR Indicator Ordering Rationale

**Location:** `docs/learned/tui/stacked-pr-indicator.md`
**Action:** UPDATE
**Source:** [PR #7974]

**Draft Content:**

Add section explaining ordering:

```markdown
## Indicator Ordering

The stacked PR indicator (pancake emoji) appears first in the indicator sequence. Rationale:

1. **Structural context** - Stacked status is fundamental to understanding the PR's relationship to other PRs
2. **Informational first** - Informational indicators precede blocking indicators
3. **Stability** - Stacked status rarely changes during PR lifecycle

The ordering rule: informational indicators (especially structural ones) precede blocking indicators (draft, conflicts, changes requested).

See `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`, `_build_indicators()` for implementation.
```

---

#### 9. Semantic Indicator Classification Table

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md`
**Action:** UPDATE
**Source:** [PR #7974]

**Draft Content:**

Add explicit classification table:

```markdown
## Indicator Classification

Indicators are classified as either **informational** (non-blocking) or **blocking**:

| Indicator | Category | Meaning |
|-----------|----------|---------|
| Stacked | Informational | PR is part of a stack |
| Eyes | Informational | Review in progress |
| Checkmark | Informational | Approved |
| Draft | Blocking | PR not ready for merge |
| Conflicts | Blocking | Merge conflicts exist |
| Changes Requested | Blocking | Reviewer requested changes |

**Rocket Rule:** The rocket (ready-to-land) indicator appears only when ALL indicators are informational. Any blocking indicator suppresses the rocket.

Do NOT enumerate specific emoji here - the classification is what matters. See source code for current emoji assignments.
```

---

#### 10. Documentation Maintenance After Refactor

**Location:** `docs/learned/documentation/refactor-doc-maintenance.md`
**Action:** CREATE
**Source:** [PR #7974]

**Draft Content:**

```markdown
---
read-when:
  - completing a refactor that changes behavior
  - searching for stale documentation
  - preparing PR for documentation review
tripwires: 1
---

# Documentation Maintenance After Refactor

Checklist for finding stale documentation after implementation changes.

## Search Strategies

After modifying code, grep for:

1. **Symbol names** - Function, class, variable names that changed
2. **Emoji characters** - If indicators changed, search for the literal emoji
3. **Feature descriptions** - Prose describing the old behavior
4. **File paths** - Documentation referencing modified files

## Example Commands

```bash
# Find docs mentioning changed function
grep -r "old_function_name" docs/learned/

# Find emoji references
grep -r "specific_emoji" docs/learned/

# Find verbatim code blocks from modified files
grep -l "lifecycle.py" docs/learned/ | xargs grep -l "```python"
```

## Prevention

- Use prose + source pointers instead of verbatim code
- Reference data structures generically, not by enumerating members
- Include source file pointers so grep can find them
```

---

### LOW Priority

#### 11. Abstraction Levels in Documentation

**Location:** `docs/learned/documentation/source-pointers.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

Add section on abstraction spectrum:

```markdown
## Abstraction Levels

Documentation drift-proneness varies by abstraction level:

1. **Verbatim code blocks** (most drift-prone) - Copy-paste of source code; drifts immediately when source changes
2. **Prose + source pointer** (preferred) - Describes what code does with pointer to canonical location; drifts when behavior changes significantly
3. **Generic references** (least drift-prone) - References data structures without enumerating contents; resilient to implementation changes

**Rule of thumb:** Use the highest abstraction level that conveys the necessary information.

- For implementation details: prose + pointer
- For volatile collections (sets, lists that grow): generic reference
- For API constants where values ARE the spec: enumeration is acceptable
```

---

#### 12. Multi-Indicator Test Coverage Pattern

**Location:** `docs/learned/testing/indicator-test-patterns.md`
**Action:** CREATE
**Source:** [PR #7974]

**Draft Content:**

```markdown
---
read-when:
  - writing tests for multi-indicator display logic
  - adding new lifecycle indicators
tripwires: 0
---

# Multi-Indicator Test Coverage

Checklist for comprehensive indicator test coverage.

## Required Test Cases

1. **Isolation** - Each indicator appears correctly in isolation
2. **Combinations** - Multiple indicators display together correctly
3. **Ordering** - Indicators appear in expected order
4. **Blocking behavior** - Blocking indicators suppress expected outcomes (e.g., rocket)
5. **Informational behavior** - Informational indicators don't block outcomes
6. **Markup integration** - Indicators render correctly in target format (terminal, HTML)

See `tests/unit/plan_store/test_lifecycle_display.py` for reference implementation.
```

---

## Stale Documentation Cleanup

**No stale documentation detected.** The ExistingDocsChecker verified all referenced code paths exist and are current. All documentation accurately reflects the codebase state.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. Documentation Drift from Refactoring

**What happened:** After refactoring the indicator logic, existing documentation still contained verbatim code showing the old implementation pattern.
**Root cause:** Verbatim code embedded in documentation becomes stale immediately when source is refactored.
**Prevention:** Use prose + source pointers instead of verbatim code. Automated bot detection in CI catches drift before merge.
**Recommendation:** TRIPWIRE (implemented in items #3 and #4 above)

### 2. Enumeration Drift Risk

**What happened:** Documentation initially enumerated specific set members ("pancake, eyes, checkmark") which would drift when new indicators are added.
**Root cause:** Overly specific prose that mirrors volatile implementation details.
**Prevention:** Reference data structures generically ("the `_non_blocking` set") without listing members.
**Recommendation:** TRIPWIRE (implemented in item #4 above)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Verbatim Code Embedding in Docs

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure +1)
**Trigger:** Before embedding exact source code in markdown documentation
**Warning:** Use prose + source pointer instead. Verbatim code creates drift risk when source changes. Bot detected 3 instances in PR #7974. See docs/learned/documentation/source-pointers.md for patterns.
**Target doc:** `docs/learned/documentation/tripwires.md`

This is tripwire-worthy because the failure mode is silent (documentation becomes stale without any error) and the pattern recurs across all documentation. The automated review bot caught this in PR #7974, demonstrating the pattern is both common and preventable.

### 2. Enumerated Set Member Drift

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** Before enumerating specific values from a set/list that may grow
**Warning:** Reference the data structure generically (e.g., "the `_non_blocking` set") not by listing members. Exception: API constants where enumeration IS the documentation.
**Target doc:** `docs/learned/documentation/tripwires.md`

This is tripwire-worthy because the failure mode is particularly insidious: documentation can be technically accurate at time of writing but becomes stale when the source collection grows. The bot detected this second-order drift risk in PR #7974.

### 3. Line Number Source Pointers

**Score:** 5/10 (Non-obvious +2, Cross-cutting +2, Silent failure +1)
**Trigger:** Before using line numbers in source pointers (e.g., `file.py:42-55`)
**Warning:** ALWAYS prefer name-based identifiers (function/class names) over line numbers. Line-based pointers are fragile and shift with code changes.
**Target doc:** `docs/learned/documentation/tripwires.md`

This is tripwire-worthy because line numbers shift with any edit to the file, making the pointer incorrect even for unrelated changes. PR #7974 review flagged 2 instances of line-number fragility.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Prose vs Enumeration Decision

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** This is a judgment call rather than a clear rule. The decision depends on whether the collection is an API constant (enumerate) or an implementation detail (reference generically). Well-addressed by the documentation items above, but may warrant tripwire if pattern violations increase.

### 2. Off-Diff Inaccuracies Limitation

**Score:** 2/10 (Cross-cutting +2)
**Notes:** This is a tooling limitation (bot can detect but can't inline comment on unchanged lines), not a coding mistake. Document as known limitation in the automated-doc-review doc rather than as a tripwire.
