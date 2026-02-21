# Documentation Plan: Fix: Add `impl-signal submitted` event to transition lifecycle stage to "implemented"

## Context

This PR fixes a critical lifecycle tracking bug where plan issues remained stuck in "implementing" stage after successful PR submission. Without this fix, `erk dash` displayed stale status for completed PRs, and users could not distinguish between in-progress and review-ready PRs. The fix adds a third event type ("submitted") to the existing `impl-signal` command, completing the lifecycle tracking for the normal PR submission flow.

The implementation establishes several documentation-worthy patterns: symmetrical integration between local and remote workflows, LBYL guards before metadata updates, and conditional workflow gating in GitHub Actions. Most importantly, it fills a documented gap in the lifecycle stage Write Points table, where `implemented` was only reachable via the `handle-no-changes` edge case.

Documentation matters here because future agents implementing similar lifecycle transitions need to understand: (1) the existing tripwire requiring LBYL checks before `update_metadata()`, (2) the design decision that not all events post comments, and (3) the graceful failure pattern used throughout the impl-signal family.

## Raw Materials

https://gist.github.com/schrockn/39556c434e7c0cc6037ab29d3283aff4

## Summary

| Metric                        | Count |
| ----------------------------- | ----- |
| Documentation items           | 7     |
| Contradictions to resolve     | 1     |
| Tripwire candidates (score>=4)| 0     |
| Potential tripwires (score2-3)| 1     |

## Documentation Items

### HIGH Priority

#### 1. Lifecycle stage Write Points table update

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
<!-- Update the Write Points table (around line 1158-1164) to add a second row for `implemented` stage -->

| Stage          | Set By                     | When                                    |
| -------------- | -------------------------- | --------------------------------------- |
| `prompted`     | `one_shot_dispatch`        | One-shot plan issue created             |
| `planning`     | `one-shot.yml` workflow    | Agent begins writing plan               |
| `planned`      | `plan_save_to_issue`, ...  | Plan saved to GitHub                    |
| `implementing` | `mark-impl-started`        | Implementation begins (local or remote) |
| `implemented`  | `impl-signal submitted`    | PR submitted successfully               |
| `implemented`  | `handle-no-changes`        | No-changes scenario (edge case)         |

<!-- Note: Two commands can set `implemented`. The primary path is `impl-signal submitted` after normal PR submission. The `handle-no-changes` command handles the edge case where implementation produces no changes. -->
```

---

#### 2. Test coverage pattern for LBYL error discrimination

**Location:** `docs/learned/testing/exec-script-testing.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
## Test Pattern: LBYL Error Discrimination

When an exec script uses LBYL checks that discriminate between error types (e.g., `PlanNotFound` vs missing config file), add test cases for each error branch:

1. **Happy path** - Verify expected outcome when all preconditions pass
2. **First error type** - Verify correct error_type when first check fails (e.g., "no-issue-reference")
3. **Second error type** - Verify correct error_type when second check fails (e.g., "issue-not-found")

See `test_impl_signal.py` for an example: the `submitted` event tests cover missing plan-ref.json (no-issue-reference) and plan issue not found (issue-not-found) as separate test cases.

Source: `tests/unit/cli/commands/exec/scripts/test_impl_signal.py`, grep for `# --- Submitted event tests ---`
```

---

### MEDIUM Priority

#### 3. `impl-signal submitted` event documentation

**Location:** `docs/learned/cli/erk-exec-commands.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
<!-- Add to the impl-signal section or create if not present -->

### impl-signal

Signals lifecycle events for plan implementation tracking. Always returns JSON and exits 0 (graceful failure pattern).

**Events:**

| Event       | Effect                                      | Requires `--session-id` |
| ----------- | ------------------------------------------- | ----------------------- |
| `started`   | Posts comment + updates metadata + cleanup  | Yes                     |
| `ended`     | Updates metadata only                       | No                      |
| `submitted` | Sets lifecycle_stage to "implemented"       | No                      |

**Key differences for `submitted`:**
- Does NOT post a GitHub comment (PR visibility is sufficient)
- Does NOT require `--session-id` flag (unlike `started`)
- Uses LBYL guard to check plan exists before updating metadata

Source: `src/erk/cli/commands/exec/scripts/impl_signal.py`, grep for `def _signal_submitted`
```

---

#### 4. Phase 5 lifecycle narrative update

**Location:** `docs/learned/planning/lifecycle.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
<!-- In Phase 5: PR Finalization & Merge section, add mention of submitted event -->

After `erk pr submit` completes successfully (or conflict resolution succeeds), the `impl-signal submitted` event is fired to transition lifecycle_stage from "implementing" to "implemented". This occurs in both local (plan-implement.md) and remote (plan-implement.yml) workflows.

The submitted event does NOT post a GitHub comment because the PR creation itself provides sufficient visibility. It only updates the plan-header metadata to enable accurate TUI display.
```

---

#### 5. Local workflow integration pattern

**Location:** `docs/learned/commands/plan-implement.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
<!-- In Step 13 (Submit PR) or appropriate location -->

## Lifecycle Stage Update After Submission

After `erk pr submit` completes, the plan-implement workflow calls:

```bash
erk exec impl-signal submitted --format json 2>/dev/null || true
```

The `2>/dev/null || true` pattern ensures graceful degradation:
- Stderr is suppressed (avoids user confusion from non-critical warnings)
- Exit code is always 0 (prevents workflow interruption if signal fails)

This maintains symmetry with the GitHub Actions workflow where the same event is fired after successful PR submission.
```

---

#### 6. GitHub Actions conditional gating pattern

**Location:** `docs/learned/ci/workflow-gating-patterns.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
## Complex Conditional for Lifecycle Stage Update

The plan-implement.yml workflow gates the `impl-signal submitted` step with a complex condition:

```yaml
if: >-
  steps.implement.outputs.implementation_success == 'true' &&
  steps.handle_outcome.outputs.has_changes == 'true' &&
  (steps.submit.outcome == 'success' || steps.handle_conflicts.outcome == 'success')
```

This ensures lifecycle stage only transitions to "implemented" when:
1. Implementation succeeded (not a failed agent run)
2. Changes exist (not a no-changes scenario handled by `handle-no-changes`)
3. Submission succeeded (either direct submit or after conflict resolution)

The `handle-no-changes` command separately sets `implemented` for zero-change scenarios.

Source: `.github/workflows/plan-implement.yml`, grep for "Update lifecycle stage to implemented"
```

---

### LOW Priority

#### 7. PR submission and lifecycle cross-reference

**Location:** `docs/learned/pr-operations/pr-submit-phases.md`
**Action:** UPDATE
**Source:** [PR #7729]

**Draft Content:**

```markdown
<!-- Add to Phase 6 or appropriate lifecycle section -->

## Lifecycle Stage Update

After successful PR submission, the lifecycle stage transitions from "implementing" to "implemented". This occurs via `impl-signal submitted` called after `erk pr submit` completes.

See [Lifecycle Stage Tracking](../planning/lifecycle.md#lifecycle-stage-tracking) for the complete list of write points and stage meanings.
```

---

## Contradiction Resolutions

### 1. Lifecycle stage "implemented" write points

**Existing doc:** `docs/learned/planning/lifecycle.md` (lines 1154-1164)
**Conflict:** The Write Points table states `implemented` stage is only set by `handle-no-changes`. This is incomplete - the normal PR submission flow did NOT update lifecycle stage.
**Resolution:** This is an ADDITIVE change, not a true contradiction. The existing documentation correctly described the incomplete behavior. Update the table to add `impl-signal submitted` as the PRIMARY write point for `implemented`, with `handle-no-changes` handling the edge case. Add a note explaining why two commands can set the same stage.

## Prevention Insights

### 1. Missing LBYL check before update_metadata()

**What happened:** The implementing agent initially missed adding the LBYL check to verify the plan exists before calling `backend.update_metadata()`. The tripwires bot caught this violation during PR review.

**Root cause:** The pattern is not obvious from the `update_metadata()` method signature. Callers assume they can pass any plan_number, but the method doesn't validate existence - it fails silently if the plan doesn't exist.

**Prevention:** The existing tripwire in `docs/learned/planning/tripwires.md` already covers this: "calling update_metadata() on PlanBackend" warns to "Always check isinstance(result, PlanNotFound) before calling update_metadata()". The tripwires bot successfully enforced this.

**Recommendation:** CONTEXT_ONLY - The tripwire already exists and worked correctly. This incident validates the system.

## Tripwire Candidates

No new tripwires meet the threshold (score >= 4). The relevant tripwire already exists in `docs/learned/planning/tripwires.md` at line 63:

> **calling update_metadata() on PlanBackend** -> Read [PlanBackend Migration Guide](plan-backend-migration.md) first. Always check isinstance(result, PlanNotFound) before calling update_metadata()

This tripwire successfully caught the missing check during PR review, demonstrating the system works as designed.

## Potential Tripwires

### 1. Test coverage for LBYL error branches

**Score:** 3/10 (Repeated pattern +1, Cross-cutting +2)
**Criteria not met:** Not destructive if missed (tests run and fail visibly); not non-obvious (standard testing practice)
**Notes:** This is good practice but belongs in testing documentation rather than tripwires. The pattern was successfully applied in this PR after feedback. Consider adding to `docs/learned/testing/exec-script-testing.md` as a recommended pattern rather than a tripwire warning.

## Validation Checklist

After documentation updates, verify:

- [ ] Write Points table includes both `impl-signal submitted` and `handle-no-changes` for `implemented` stage
- [ ] Note explains why two commands can set the same stage
- [ ] `erk-exec-commands.md` documents all three impl-signal events with their differences
- [ ] Test pattern for LBYL error discrimination is documented with example reference
- [ ] Cross-references are bidirectional (lifecycle.md <-> plan-implement.md, lifecycle.md <-> pr-submit-phases.md)
- [ ] No private function names (`_signal_submitted`) appear in learned docs - use conceptual descriptions
