# Documentation Plan: Fix rocket emoji appearing on draft PRs in lifecycle display

## Context

PR #8061 fixed a UI bug where draft PRs in the erk dashboard incorrectly displayed the rocket emoji (🚀) indicating "ready to land" status. The bug was subtle: draft PRs can have passing CI, no conflicts, approved reviews, and no unresolved comments — all the conditions that normally trigger the rocket. But draft PRs cannot be merged on GitHub, so showing the rocket was misleading. Users would see 🚧 🚀 together, sending contradictory signals.

The fix added `is_draft is not True` to the rocket condition in `_build_indicators()`. This was a clean, single-location fix that touched only two files: the implementation in `lifecycle.py` and the corresponding test that was asserting the broken behavior.

Documentation matters here because the existing docs correctly described the *intent* — blocking indicators should prevent the rocket — but didn't explicitly enumerate draft status as a blocking indicator. The bug occurred because the ready-to-land condition evolved organically over time (adding checks for conflicts, review decisions, checks passing, unresolved comments) without anyone remembering to check draft status. A future developer adding similar indicator logic could make the same mistake. The documentation update makes the rule explicit, and a tripwire prevents regression.

## Raw Materials

PR #8061 session data (no gist URL provided)

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 2     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 1     |
| Potential tripwires (score2-3) | 0     |

## Documentation Items

### HIGH Priority

#### 1. Draft status as blocking indicator

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md`
**Action:** UPDATE
**Source:** [PR #8061]

**Draft Content:**

```markdown
Update the "Blocking vs. Informational Indicators" section (lines 63-74) to explicitly list draft status as a blocking indicator.

In the existing bullet list after "Examples: CI failures, unresolved review comments, merge conflicts." add:

- **Draft status (🚧)** — Draft PRs cannot be merged on GitHub. The rocket emoji must never appear on draft PRs regardless of other indicator states. See PR #8061 for the fix that enforced this rule in `_build_indicators()`.

This makes the implicit rule explicit. The existing prose "blocking indicators prevent the rocket emoji from appearing" described the intent correctly, but the examples list didn't include draft status. Future developers modifying indicator logic need to see draft status explicitly enumerated alongside CI failures and merge conflicts.
```

---

#### 2. Draft PR blocking tripwire

**Location:** `docs/learned/desktop-dash/visual-status-indicators.md` (frontmatter)
**Action:** UPDATE
**Source:** [PR #8061]

**Draft Content:**

```markdown
Add a new tripwire to the frontmatter of visual-status-indicators.md:

tripwires:
  - action: "Adding ready-to-land or mergeable indicator logic without checking is_draft"
    warning: "Draft PRs cannot be merged and must never show the rocket emoji. Add `is_draft is not True` to the condition alongside other blocking checks (conflicts, review decisions, failing checks). See PR #8061."
    score: 6

This tripwire will be auto-synced to docs/learned/desktop-dash/tripwires.md by `erk docs sync`.

Why this location: The tripwire belongs with the visual-status-indicators doc because that's the canonical reference for indicator semantics. When an agent reads about blocking vs. informational indicators, the tripwire will already be in context.

Why score 6:
- Non-obvious (+2): Draft PRs *look* ready (passing CI, no conflicts, approved reviews) but cannot be merged
- Cross-cutting (+2): Any ready-to-land logic must check draft status — this applies to lifecycle indicators, PR commands, automated workflows
- Silent failure (+2): No exception is thrown; the wrong indicator simply appears, misleading users
```

---

### MEDIUM Priority

None

### LOW Priority

None

## Contradiction Resolutions

**No contradictions found.**

The existing documentation correctly describes the intended behavior. The bug was in the implementation (missing `is_draft` check), not the documentation. The "Blocking vs. Informational Indicators" section accurately explains that blocking indicators prevent the rocket — draft status simply wasn't enumerated in the examples list.

## Stale Documentation Cleanup

**No stale documentation found.**

All referenced files in existing docs were confirmed to exist:
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py` (EXISTS)
- `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/real.py` (EXISTS)

## Prevention Insights

### 1. Line length lint error after adding condition

**What happened:** Adding `is_draft is not True and` to the existing single-line boolean expression pushed the line to 113 characters, triggering Ruff lint E501 (line too long, max 100).

**Root cause:** The original boolean expression was already near the character limit. Adding another condition pushed it over.

**Prevention:** When a boolean expression has 3+ conditions or approaches 80 characters, wrap it in parentheses with one condition per line preemptively rather than waiting for lint to fail.

**Recommendation:** SHOULD_BE_CODE — This is a linting rule, not a learned pattern. It belongs in the `dignified-python` skill or linter configuration, not in learned docs.

## Tripwire Candidates

### 1. Draft PR blocking check missing

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure +2)

**Trigger:** Before implementing ready-to-land or mergeable indicators

**Warning:** Draft PRs cannot be merged and must never show the rocket emoji. Add `is_draft is not True` to the condition alongside other blocking checks (conflicts, review decisions, failing checks). See PR #8061.

**Target doc:** `docs/learned/desktop-dash/visual-status-indicators.md`

This bug is tripwire-worthy because it involves conflicting visual signals that confuse users. The rocket emoji says "ready to merge" while the draft indicator says "not ready." The root cause is that draft status is semantically different from other blocking conditions — a draft PR can have *all* the positive signals (passing CI, approved reviews, no conflicts) yet still be unmergeable. Without the tripwire, future developers adding similar indicator logic will likely focus on the obvious blocking conditions (CI failures, conflicts) and forget to check draft status.

## Potential Tripwires

**No items with score 2-3.**

## Skipped Items

| Item | Reason | Existing Doc (if applicable) |
|------|--------|------------------------------|
| `test_impl_draft_checks_passing_no_rocket()` | Test correction aligns with fixed implementation; no new cross-cutting insight | N/A |
| Multi-line boolean formatting pattern | Belongs in dignified-python skill or linter config, not learned docs | N/A |
| `_build_indicators()` method signature | Single-artifact API reference belongs in docstring, not learned docs | N/A |
| Test pattern for lifecycle indicators | Existing test suite patterns are sufficient; no new insight discovered | `docs/learned/testing/testing.md` |

## Implementation Notes

### Priority Order

1. **First:** Add tripwire to `docs/learned/desktop-dash/visual-status-indicators.md` frontmatter
   - Prevents future regressions
   - Quick to implement
   - High impact (cross-cutting concern)

2. **Second:** Update the "Blocking vs. Informational Indicators" section body
   - Makes implicit rule explicit
   - Adds draft status to blocking indicators list
   - Cross-reference to PR #8061 for traceability

3. **Third:** Run `erk docs sync` to regenerate `docs/learned/desktop-dash/tripwires.md`

### Source Pointers

For locating modified code:

1. **Function:** `_build_indicators()`
   - Path: `packages/erk-shared/src/erk_shared/gateway/plan_data_provider/lifecycle.py`
   - Lines: 225-231 (rocket emoji condition)
   - Grep: `def _build_indicators`

2. **Test:** `test_impl_draft_checks_passing_no_rocket()`
   - Path: `tests/unit/plan_store/test_lifecycle_display.py`
   - Lines: 476-486
   - Grep: `test_impl_draft_checks_passing_no_rocket`

### Cross-references to Maintain

- Tripwire in visual-status-indicators.md references PR #8061
- Body text update in visual-status-indicators.md references PR #8061
- Both updates are in the same file, keeping related content together
