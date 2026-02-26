# Documentation Plan: Delete get_branch_issue() dead code and simplify to plan-ref.json

## Context

This PR (#8269) completes a significant architectural migration in erk's plan resolution system. Previously, erk supported two mechanisms for associating plans with branches: (1) extracting plan IDs from branch names using P-prefix patterns like `P4655-feature`, and (2) explicit storage via `.impl/plan-ref.json` files. PR #8071 introduced `plan-ref.json` and stopped encoding plan IDs in new branch names, switching to the `plnd/` prefix format. This PR removes the last consumer of branch-name-based plan resolution—the `get_branch_issue()` gateway method—making `plan-ref.json` the sole authoritative source.

The documentation updates serve two purposes: (1) correcting existing docs that still reference the deprecated branch-name resolution pattern, and (2) capturing the patterns demonstrated by this clean gateway method removal. Future agents working on similar migrations or gateway removals will benefit from understanding that P-prefix branches are legacy, that `plan-ref.json` is the single source of truth, and that gateway method removals must update all five implementation places (ABC, Real, Fake, DryRun, Printing).

Additionally, the audit-pr-docs bot proved highly effective at catching semantic drift during this PR's review—identifying three inaccuracies in linear-pipelines.md, one verbatim code copy in optional-arguments.md, and one terminology inconsistency. These findings warrant documentation of the bot's capabilities for future reference.

## Raw Materials

PR #8269: Delete get_branch_issue() dead code and simplify to plan-ref.json

## Summary

| Metric                        | Count |
| ----------------------------- | ----- |
| Documentation items           | 9     |
| Contradictions to resolve     | 1     |
| Tripwire candidates (score>=4)| 0     |
| Potential tripwires (score2-3)| 2     |

## Documentation Items

### HIGH Priority

#### 1. Update plan-ref.json authoritative source documentation

**Location:** `docs/learned/architecture/plan-ref-architecture.md`, `docs/learned/architecture/issue-reference-flow.md`, `docs/learned/erk/issue-pr-linkage-storage.md`
**Action:** UPDATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
## Migration Complete: plan-ref.json as Sole Source

As of PR #8269, `get_branch_issue()` has been removed from the gateway. The branch-naming inference pattern is fully deprecated:

- **Legacy (P-prefix)**: Branches named `P{issue}-{slug}` no longer provide plan IDs
- **Current (plnd/)**: All plan-to-branch mapping uses `.impl/plan-ref.json` exclusively

See `packages/erk-shared/src/erk_shared/impl_folder.py` for `read_plan_ref()` implementation.
```

---

#### 2. Fix semantic staleness in linear-pipelines.md

**Location:** `docs/learned/architecture/linear-pipelines.md`
**Action:** UPDATE
**Source:** [PR #8269] (audit-pr-docs bot findings)

**Draft Content:**

```markdown
## Corrections Needed

Line 82: Change claim about `plan_issue_number` derivation. The field is set to `None` by `make_execution_state()`, not re-derived from plan-ref.json.

Line 76: Correct field name usage. The field is `plan_id`, not `plan_issue_number`.

Lines 156-159: Update pipeline steps list. Actual code has 3 steps, not 4. Remove reference to non-existent `update_objective` step.

See `src/erk/cli/commands/pr/submit_pipeline/` for current pipeline implementation.
```

---

#### 3. Resolve P-prefix terminology contradiction

**Location:** `docs/learned/planning/branch-plan-resolution.md`
**Action:** UPDATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
## Legacy vs Current Branch Naming

Around line 40, change "standard plan branches" to "legacy plan branches" when referring to P-prefix format.

Add clarification:
- **Legacy format**: `P{issue}-{slug}` (e.g., `P4655-feature`) — no longer provides plan IDs
- **Current format**: `plnd/{slug}` — introduced in PR #8071, requires `plan-ref.json` for plan association

Note: `extract_leading_issue_number()` still exists but always returns `None`.
```

---

#### 4. Convert verbatim code to source pointer format

**Location:** `docs/learned/cli/optional-arguments.md`
**Action:** UPDATE
**Source:** [PR #8269] (audit-pr-docs bot recommendation)

**Draft Content:**

```markdown
## Line 38 Update

Replace verbatim code copy with source pointer format:

**Before**: Inline code block copying implementation
**After**: Reference to source file

The plan resolution pattern is implemented in `src/erk/cli/commands/wt/list_cmd.py`. Search for `def _get_impl_issue` to see the priority order:
1. Check explicit CLI argument
2. Fall back to `read_plan_ref()` on `.impl/plan-ref.json`
3. Raise ClickException if neither source provides a value
```

---

#### 5. Complete migration documentation

**Location:** `docs/learned/architecture/ref-json-migration.md`
**Action:** UPDATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
## Migration Complete

Add section noting that PR #8269 completes the migration:

### Phase 2 Complete: get_branch_issue() Removal

The removal of `get_branch_issue()` in PR #8269 completes the migration away from branch-name-based plan resolution:

- **Phase 1 (PR #8071)**: Introduced `plan-ref.json`, switched new branches from `P{issue}-{slug}` to `plnd/{slug}`
- **Phase 2 (PR #8269)**: Removed `get_branch_issue()` gateway method (always returned `None`)

Result: Branch names are now purely descriptive. Plan-to-branch mapping is explicit via `plan-ref.json` only.
```

---

### MEDIUM Priority

#### 6. Document function signature migration pattern

**Location:** `docs/learned/cli/tripwires.md`
**Action:** CREATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
# CLI Tripwires

## Function Signature Migration Pattern

When removing fallback logic from helper functions, consider making previously-optional parameters keyword-only to force callers to be explicit.

### Example: _get_impl_issue() Signature Change

See `src/erk/cli/commands/wt/list_cmd.py` for the `_get_impl_issue` function.

**Pattern**: When removing a fallback (like git config lookup), change:
- `branch: str | None = None` (optional with default)
- To: `branch: str | None` (keyword-only, still nullable)

This forces call sites to be explicit: `_get_impl_issue(ctx, worktree_path, branch=branch)`

**When to keep nullable**: Detached HEAD states are valid (branch is `None`). The nullability preserves this case while removing the implicit fallback behavior.
```

---

#### 7. Document automated review bot capabilities

**Location:** `docs/learned/ci/automated-review-bots.md`
**Action:** CREATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
# Automated Review Bots

Erk uses several automated bots for PR review. These bots catch issues that human reviewers might miss.

## audit-pr-docs

Detects documentation drift by comparing claims in `docs/learned/` to actual code.

**Capabilities:**
- Semantic staleness detection (e.g., incorrect field derivation claims)
- Verbatim code copy detection (flags maintenance burden)
- Terminology inconsistency detection (e.g., legacy vs current conventions)

**Example findings from PR #8269:**
- Caught 3 inaccuracies in linear-pipelines.md
- Flagged 1 verbatim code copy in optional-arguments.md

## test-coverage-review

Analyzes coverage gaps and identifies legitimately untestable code.

## dignified-code-simplifier

Verifies dignified-python compliance in changed files.

## tripwires-review

Uses tiered pattern matching:
- **Tier 1**: Mechanical grep for known anti-patterns
- **Tier 2**: Semantic matches requiring context analysis
```

---

#### 8. Enhance source pointer documentation

**Location:** `docs/learned/documentation/source-pointers.md`
**Action:** UPDATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
## Additional Examples

Add examples showing the problem and solution:

### Anti-pattern: Verbatim Code Copy

Copying code into documentation creates maintenance burden. When the code changes, the documentation silently becomes inaccurate.

### Correct Pattern: Source Reference

Instead of copying code, reference it:

> The plan resolution priority is implemented in `src/erk/cli/commands/wt/list_cmd.py`. Search for `def _get_impl_issue` to see the implementation.

This ensures agents read the current code rather than stale documentation.

### When Short Snippets Are Acceptable

Short illustrative snippets (5 lines or fewer) showing a pattern are acceptable when:
- The pattern is stable and unlikely to change
- The snippet demonstrates a concept, not an implementation detail
```

---

#### 9. Document field naming conventions

**Location:** `docs/learned/reference/field-naming-conventions.md`
**Action:** CREATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
# Field Naming Conventions

Definitive guide for plan-related field names in erk.

## Plan Identifier Fields

| Field Name | Type | Usage |
|------------|------|-------|
| `plan_id` | int | GitHub issue number of the plan issue |
| `plan_issue_number` | int | Synonym for `plan_id` (prefer `plan_id`) |
| `plan_number` | int | Display-only number (may include objective context) |

## Context

PR #8269 highlighted confusion around these terms when the audit-pr-docs bot found inconsistent usage in linear-pipelines.md.

## Guideline

- Use `plan_id` as the canonical field name for the GitHub issue number
- Use `plan_number` only in display/UI contexts
- Avoid `plan_issue_number` in new code (legacy synonym)
```

---

### LOW Priority

#### 10. Add historical example to gateway decomposition

**Location:** `docs/learned/architecture/gateway-decomposition-phases.md`
**Action:** UPDATE
**Source:** [PR #8269]

**Draft Content:**

```markdown
## Phase 8: The Convenience Method Purge

Add example:

### Example: get_branch_issue() Removal (PR #8269)

The `get_branch_issue()` method on `BranchOpsGateway` was a convenience method that extracted plan IDs from branch names. After PR #8071 switched to `plnd/` branch naming, this method always returned `None`.

PR #8269 removed this dead code from all five gateway implementations:
- `abc.py` (abstract method definition)
- `real.py` (real implementation)
- `fake.py` (fake implementation + constructor parameter)
- `dry_run.py` (dry-run wrapper)
- `printing.py` (printing wrapper)

This demonstrates the clean removal pattern: when a gateway method becomes a no-op, remove it completely rather than leaving deprecated code.
```

## Contradiction Resolutions

### 1. P-prefix branch naming terminology

**Existing doc:** `docs/learned/planning/branch-plan-resolution.md:40`
**Conflict:** Document calls P-prefix branches "standard plan branches" when they are actually legacy. The current standard is `plnd/` prefix since PR #8071.
**Resolution:** Update line 40 to use "legacy plan branches" terminology. Add note that `plnd/` is the current standard and requires `plan-ref.json` for plan association.

## Stale Documentation Cleanup

No phantom file references detected. All semantic staleness issues are covered by the HIGH priority update items (linear-pipelines.md, optional-arguments.md).

## Prevention Insights

### 1. Two-Phase Deprecation Pattern

**What happened:** The migration from branch-name-based plan resolution to `plan-ref.json` was executed cleanly over two PRs.
**Root cause:** Legacy systems that are partially deprecated create confusion about which system is authoritative.
**Prevention:** Use a two-phase approach:
- Phase 1: Add new system, make old system return sentinel values, update docs to mark old as legacy
- Phase 2: Remove dead code after confirming no active consumers

**Recommendation:** ADD_TO_DOC - This pattern is valuable for future deprecations but doesn't warrant a tripwire (not a common error).

### 2. Semantic Documentation Drift

**What happened:** Three inaccuracies were found in linear-pipelines.md that had accumulated over time.
**Root cause:** Documentation claims about code behavior were not verified against actual implementation.
**Prevention:** The audit-pr-docs bot now catches these issues during PR review. Consider periodic full-repo audits beyond PR-level checks.

**Recommendation:** ADD_TO_DOC - Document the bot capabilities so future developers trust and respond to its findings.

## Tripwire Candidates

No items met the tripwire-worthiness threshold (score >= 4). The gateway ABC method removal pattern is already documented as a tripwire in `docs/learned/architecture/gateway-abc-implementation.md`.

## Potential Tripwires

Items with score 2-3 that may warrant promotion with additional context:

### 1. Function signature keyword-only migration pattern

**Score:** 3/10 (Non-obvious +2, Cross-cutting +1)
**Notes:** Applies when removing fallback logic from helpers. The pattern of converting `param: Type = None` to `param: Type` (keyword-only) forces callers to be explicit. Not destructive enough for full tripwire status since forgetting it doesn't break functionality—it just reduces code clarity.

### 2. Semantic documentation staleness

**Score:** 3/10 (Non-obvious +2, Repeated pattern +1)
**Notes:** The audit-pr-docs bot caught 3 instances in one PR, suggesting documentation claims can drift from implementation. A tripwire could remind agents to verify claims against code, but the bot already serves this function. May warrant promotion if bot coverage gaps are identified.
