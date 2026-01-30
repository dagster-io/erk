# Documentation Plan: Convert push_to_remote and pull_rebase to Discriminated Unions

## Context

This refactoring converted two core Git gateway methods (`push_to_remote` and `pull_rebase`) from exception-raising patterns to discriminated union return types (`PushResult | PushError` and `PullRebaseResult | PullRebaseError`). The work demonstrates mature application of erk's established architectural patterns: discriminated unions for error handling, the 5-place gateway implementation pattern, and LBYL error checking.

The implementation touched 18 files across the codebase, including all 5 gateway implementation layers (ABC, real, fake, dry-run, printing), 8 caller sites that required migration to the new return types, and comprehensive fake layer tests. This is significant documentation material because future agents performing similar gateway refactorings need concrete examples of both the implementation pattern and the systematic caller migration approach.

The key non-obvious insight from this work is the error handling responsibility distribution: try/except blocks belong in the `real.py` boundary (where subprocess execution occurs), while fake/dry-run/printing implementations return proper discriminated union instances directly. This subtle architectural decision prevents exception leakage and maintains clean separation of concerns.

## Raw Materials

https://gist.github.com/schrockn/492830f99e180d4410272f80c4709db1

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 2     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Add Git Remote Operations Exemplar to Discriminated Union Doc

**Location:** `docs/learned/architecture/discriminated-union-error-handling.md`
**Action:** UPDATE_EXISTING
**Source:** [Impl] [PR #6329]

Add PushResult/PushError and PullRebaseResult/PullRebaseError as concrete exemplars showing the pattern applied to git remote operations, with both fire-and-forget and error-reporting caller patterns.

**Reference:** `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py`

#### 2. Add Git Remote Ops as 5-Place Pattern Reference

**Location:** `docs/learned/architecture/gateway-abc-implementation.md`
**Action:** UPDATE_EXISTING
**Source:** [Impl] [PR #6329]

Document git remote operations as reference example for 5-place implementation pattern (abc, real, fake, dry-run, printing), with emphasis on error handling responsibility distribution.

**Reference:** `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/`

#### 3. Create Gateway Error Boundaries Documentation

**Location:** `docs/learned/architecture/gateway-error-boundaries.md`
**Action:** NEW_DOC
**Source:** [Impl] [PR #6329]

Document the pattern where try/except blocks belong in real.py boundary (where subprocess execution occurs), while fake/dry-run/printing implementations return discriminated union instances directly. Include explicit anti-pattern warning about exception leakage.

#### 4. Add Gateway ABC Modification Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** TRIPWIRE
**Source:** [Plan] [Impl]
**Tripwire Score:** 6/10

Add reminder: "Before modifying a gateway ABC method signature, ensure all 5 implementations are updated simultaneously: abc.py, real.py, fake.py, dry_run.py, printing.py."

### MEDIUM Priority

#### 5. Create Parameter Naming Semantics Documentation

**Location:** `docs/learned/architecture/parameter-naming-semantics.md`
**Action:** NEW_DOC
**Source:** [Impl]

Document naming convention: `*_error` suffix for methods returning discriminated unions vs deprecated `*_raises` for exception-raising methods. Include migration pattern for renaming parameters during conversions.

#### 6. Create Gateway Fake Testing Exemplar

**Location:** `docs/learned/testing/gateway-fake-testing-exemplar.md`
**Action:** NEW_DOC
**Source:** [Impl] [PR #6329]

Use `tests/unit/fakes/test_fake_git_remote_ops.py` as exemplar showing how to test fake implementations that return discriminated unions, with both success and error path verification.

#### 7. Create Gateway Signature Migration Pattern

**Location:** `docs/learned/architecture/gateway-signature-migration.md`
**Action:** NEW_DOC
**Source:** [Impl] [PR #6329]

Document systematic pattern for updating all call sites when gateway method signatures change: 1) Discover all sites via grep, 2) Update gateway implementations (5 places), 3) Migrate each caller with appropriate error handling, 4) Update tests.

Reference: PR #6329 migrated 8 call sites across 7 files atomically.

#### 8. Add Systematic Call Site Discovery Tripwire

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** TRIPWIRE
**Source:** [Plan] [Impl]
**Tripwire Score:** 5/10

Add reminder: "Before changing any gateway method signature, search for ALL callers with grep. Document the count. Missing a call site causes runtime failures."

### LOW Priority

#### 9. Create Test Layer Responsibility Documentation

**Location:** `docs/learned/testing/test-layer-responsibility.md`
**Action:** NEW_DOC
**Source:** [Impl] [PR #6329]

Document 3-layer testing model: Layer 1 (fakes verify return behavior), Layer 2 (integration tests), Layer 3 (business logic tests). Helps respond to coverage questions by clarifying where each behavior should be tested.

#### 10. Create Breaking Change Migration Pattern

**Location:** `docs/learned/architecture/breaking-change-migration.md`
**Action:** NEW_DOC
**Source:** [Impl] [PR #6329]

Document pattern for converting exception-raising methods to discriminated unions atomically: inventory call sites → define types → update gateway (5 places) → migrate callers → update tests.

## Prevention Insights

No significant errors or failed approaches were documented in the session analyses. The implementation followed established patterns correctly.

## Tripwire Candidates

### HIGH Threshold (Score >= 4)

| Candidate | Score | Trigger | Warning |
|-----------|-------|---------|---------|
| Gateway ABC modification requires 5-place update | 6 | Modifying gateway ABC method signature | Must update all 5 implementations: abc, real, fake, dry_run, printing |
| Systematic call site discovery required | 5 | Changing any gateway method signature | Search for ALL callers via grep; missing one causes runtime failures |

### POTENTIAL Threshold (Score 2-3)

- Error handling at boundaries (score 3) - May warrant promotion if pattern violations increase
- Parameter semantic renaming (score 2) - Low frequency pattern; only during exception→union conversions