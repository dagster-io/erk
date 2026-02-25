# Documentation Plan: Strengthen LBYL guard for plan metadata field validation

## Context

This plan captures learnings from PR #8126, which fixed a bug in the best-effort metadata update path. The existing LBYL guard in `maybe_update_plan_dispatch_metadata()` only checked for the presence of `schema_version`, allowing incomplete plan-header blocks (with schema_version but missing `created_at`/`created_by`) to pass validation. When `update_metadata()` later attempted to merge fields and validate with `PlanHeaderSchema`, it would raise `ValueError` on missing required fields — a crash in a function whose contract is "skip silently."

The fix strengthens the guard to check ALL required fields using `get_all_metadata_fields()` and set operations, adding a user-facing warning when metadata is incomplete. This prevents crashes during landing operations, where a hard error would "grind everything to a halt" according to user context. The implementation sessions also revealed important patterns around stderr routing for `user_output()` that caused a test assertion failure — tests must check `capsys.readouterr().err`, not `.out`.

These learnings matter because they establish cross-cutting patterns: comprehensive LBYL validation for best-effort operations, warning message formatting for silent skips, and the stderr routing behavior that affects all tests using `user_output()`. The Explore subagent also produced a detailed lifecycle report covering plan metadata creation, reading, and updating paths that would help future agents understand the system.

## Raw Materials

PR #8126

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 7     |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 1     |

## Documentation Items

### HIGH Priority

#### 1. user_output() stderr routing

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## user_output() stderr routing

When testing code that calls `user_output()`, always assert against `capsys.readouterr().err`, not `.out`.

The `user_output()` function routes messages to stderr by design. This enables shell integration where structured data (JSON, etc.) goes to stdout while user-facing messages go to stderr.

See `src/erk/cli/helpers/output.py` for the implementation.

**Common mistake:**
```python
# WRONG - user_output goes to stderr
captured = capsys.readouterr()
assert "message" in captured.out

# CORRECT
captured = capsys.readouterr()
assert "message" in captured.err
```
```

---

#### 2. LBYL guard for best-effort operations

**Location:** `docs/learned/architecture/erk-architecture.md` (tripwires section)
**Action:** UPDATE
**Source:** [Impl], [PR #8126]

**Draft Content:**

```markdown
## Comprehensive LBYL for best-effort functions

When implementing `maybe_*` functions that should silently skip on errors, use LBYL guards to check ALL preconditions before calling operations that might raise.

**Pattern**: Use `get_all_metadata_fields()` and check required field set with set operations:

```python
required_fields = {"schema_version", "created_at", "created_by"}
missing = required_fields - all_metadata.keys()
if missing:
    # Warn and return instead of raising
    return
```

Single-field checks (e.g., only checking `schema_version`) miss incomplete metadata blocks. See `metadata_helpers.py` for the canonical implementation.

**Why this matters**: The assertive path (`write_dispatch_metadata`) doesn't need this guard because it operates on plans erk just created (guaranteed complete). The best-effort path handles "might be a plan" scenarios where operations shouldn't crash on incomplete metadata.
```

---

#### 3. Plan metadata lifecycle

**Location:** `docs/learned/planning/plan-metadata-lifecycle.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: understanding plan metadata creation/reading/updating, debugging incomplete metadata
---

# Plan Metadata Lifecycle

Plan metadata flows through distinct creation, reading, and updating phases.

## Creation Paths

All creation paths write complete required fields (`schema_version`, `created_at`, `created_by`):

- `create_plan_issue()` - standard plan creation
- `PlannedPRBackend.create_plan()` - PR-driven plans
- `one_shot_dispatch.py` - remote dispatch plans

All funnel through `format_plan_header_body()` which calls `create_plan_header_block()`. See `src/erk/cli/commands/pr/` for creation paths.

## Reading Methods

- `get_metadata_field()` - single field lookup (used by 7+ commands: submit, view, land, learn, etc.)
- `get_all_metadata_fields()` - full dict (used by `maybe_update_plan_dispatch_metadata` for comprehensive validation)

## Updating Methods

- `update_metadata()` - sole mutation path, validates with `PlanHeaderSchema`
- `maybe_update_plan_dispatch_metadata()` - best-effort wrapper, uses LBYL guards
- `write_dispatch_metadata()` - assertive wrapper, raises on failure

## Why Incomplete Metadata Exists

Despite creation always writing complete headers, incomplete headers arise from:

1. **Non-erk-plan issues** - branch name matches P{number} but issue has hand-edited/partial metadata
2. **Manual edits** - user edited issue body on GitHub
3. **Pre-schema-v2 issues** - older tooling wrote partial blocks
4. **Truncated writes** - GitHub API accepted issue creation but body was corrupted/truncated
```

---

### MEDIUM Priority

#### 4. Best-effort vs assertive update patterns

**Location:** `docs/learned/planning/metadata-update-patterns.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
---
read-when: implementing metadata update functions, choosing between silent skip and raise
---

# Metadata Update Patterns

The codebase has two distinct update contracts for plan metadata.

## Assertive Path

`write_dispatch_metadata()` raises on failure. Used by one-shot dispatch on plans that erk just created (guaranteed complete metadata).

## Best-Effort Path

`maybe_update_plan_dispatch_metadata()` silently skips when metadata is incomplete or missing. Used after `erk pr launch` on arbitrary branches that might be plans.

## When to Use Which

- **Assertive**: When you control creation and can guarantee complete metadata
- **Best-effort**: When operating on user-provided input that "might be a plan"

## LBYL Guard Requirement

Best-effort functions must use LBYL guards to check ALL required fields before calling operations that might raise. See `metadata_helpers.py` for the canonical pattern.

## Design Rationale

Metadata update shouldn't block landing operations. The dispatch metadata (`last_dispatched_run_id`, etc.) is informational — losing it is far less costly than blocking a land/launch.
```

---

#### 5. User-facing warning on silent skip

**Location:** `docs/learned/cli/cli-ux-patterns.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8126]

**Draft Content:**

```markdown
## Warning Messages for Silent Skips

When an LBYL guard causes a function to skip silently, emit a warning showing why the skip occurred.

**Pattern components:**
1. Warning symbol (yellow)
2. What was incomplete
3. Which specific fields are missing
4. What action was skipped

**Example from `metadata_helpers.py`:**
```python
user_output(
    click.style("⚠", fg="yellow")
    + f" Plan #{plan_id} has incomplete plan-header"
    + f" (missing {', '.join(sorted(missing))}), skipping dispatch metadata update"
)
```

This pattern helps users understand what happened without blocking operations.
```

---

#### 6. Comprehensive metadata validation pattern

**Location:** `docs/learned/planning/comprehensive-validation.md`
**Action:** CREATE
**Source:** [PR #8126]

**Draft Content:**

```markdown
---
read-when: validating plan metadata before operations, implementing LBYL guards
---

# Comprehensive Metadata Validation

When validating plan metadata, check ALL required fields rather than a single sentinel field.

## Pattern

```python
all_metadata = ctx.plan_backend.get_all_metadata_fields(repo.root, plan_id)
if isinstance(all_metadata, PlanNotFound):
    return

required_fields = {"schema_version", "created_at", "created_by"}
missing = required_fields - all_metadata.keys()
if missing:
    # Handle incomplete metadata
    pass
```

## Why This Matters

Single-field checks miss incomplete metadata blocks. A plan-header with `schema_version` but missing `created_at`/`created_by` would pass validation and cause `ValueError` when `PlanHeaderSchema.validate()` runs.

## When to Apply

- Best-effort operations (`maybe_*` functions)
- Pre-validation before mutation operations
- Any code path where incomplete metadata should skip rather than crash

See `metadata_helpers.py:maybe_update_plan_dispatch_metadata()` for the canonical implementation.
```

---

### LOW Priority

#### 7. Schema validation error propagation prevention

**Location:** `docs/learned/architecture/erk-architecture.md` (LBYL principles section)
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## Error Propagation Prevention

LBYL guards prevent `ValueError` from `PlanHeaderSchema.validate()` from propagating through functions whose contract is "skip silently."

When a function has best-effort semantics (e.g., `maybe_*` prefix), validation errors should be caught before calling update operations. The guard should check all preconditions that the downstream validation will require.
```

---

## Contradiction Resolutions

No contradictions detected. All existing documentation is consistent with the changes in this PR.

## Stale Documentation Cleanup

No stale documentation identified. All existing docs have valid references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. ValueError crash in best-effort metadata update

**What happened:** `maybe_update_plan_dispatch_metadata()` allowed incomplete plan-header blocks through to `update_metadata()`, which then crashed with `ValueError` when `PlanHeaderSchema.validate()` found missing required fields.

**Root cause:** The LBYL guard only checked for `schema_version`, assuming its presence meant complete metadata. Incomplete headers with schema_version but missing `created_at`/`created_by` passed the guard.

**Prevention:** Check ALL required fields using `get_all_metadata_fields()` and set operations: `required_fields.issubset(all_metadata.keys())` or `required_fields - all_metadata.keys()` to detect missing fields.

**Recommendation:** TRIPWIRE (score 6)

### 2. Test assertion on wrong output stream

**What happened:** Test asserted `"incomplete plan-header" in captured.out` but the assertion failed.

**Root cause:** `user_output()` routes to stderr (`err=True` in `click.echo()`) for shell integration — structured data on stdout, user messages on stderr.

**Prevention:** When testing code that calls `user_output()`, always check `capsys.readouterr().err` not `.out`.

**Recommendation:** TRIPWIRE (score 6)

### 3. Silent failures without context

**What happened:** Initial implementation returned silently when LBYL guard triggered, leaving users confused about why operation was skipped.

**Root cause:** User specifically requested warning message (line 204: "yes have it warn though").

**Prevention:** When LBYL guard causes a function to skip silently, emit a warning with `user_output()` showing specific missing/invalid fields before returning.

**Recommendation:** TRIPWIRE (score 4)

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. user_output() stderr routing

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Silent failure +2)
**Trigger:** When testing code that calls `user_output()`
**Warning:** Always assert against `capsys.readouterr().err`, not `.out`. The `user_output()` function routes to stderr for shell integration (structured data on stdout, user messages on stderr).
**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because the failure mode is silent — the test simply fails with "string not in output" without explaining that the string is actually in stderr. Both implementation sessions hit this exact issue, suggesting it will recur.

### 2. LBYL guard for best-effort operations

**Score:** 6/10 (criteria: Non-obvious +2, Cross-cutting +2, Destructive potential +2)
**Trigger:** When implementing `maybe_*` functions that should silently skip on errors
**Warning:** Use LBYL guards to check ALL preconditions before calling operations that might raise. Use `get_all_metadata_fields()` and check required field set with `required_fields.issubset(all_metadata.keys())`. Single-field checks miss incomplete metadata blocks. See `metadata_helpers.py:maybe_update_plan_dispatch_metadata()` for the pattern.
**Target doc:** `docs/learned/architecture/erk-architecture.md` (tripwires section)

This tripwire has HIGH real-world impact — the incomplete guard blocked landing operations in production, "grinding everything to a halt." The pattern is cross-cutting because any best-effort function with validation requirements needs comprehensive precondition checking.

### 3. Warn on silent skips

**Score:** 4/10 (criteria: Non-obvious +2, Cross-cutting +2)
**Trigger:** When LBYL guard causes a function to skip silently
**Warning:** Emit a warning with `user_output()` showing why the skip occurred (what's incomplete, which fields are missing, what action was skipped). Helps users understand what happened without blocking operations.
**Target doc:** `docs/learned/architecture/erk-architecture.md` (LBYL principles section)

While not as severe as the other tripwires, this pattern improves UX significantly. User specifically requested it during implementation, indicating it wasn't obvious from the initial design.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Incomplete metadata causes

**Score:** 3/10 (criteria: Non-obvious +2, External tool quirk +1)
**Notes:** The four causes of incomplete metadata (non-erk-plan issues, manual edits, pre-schema-v2 issues, truncated API writes) are documented in the lifecycle doc. This doesn't meet tripwire threshold because it's reference information rather than actionable prevention guidance. May warrant tripwire status if agents repeatedly investigate "why is metadata incomplete?" during debugging sessions.
