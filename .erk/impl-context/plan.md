# Documentation Plan: Fix: Remove unsupported `branch_slug` parameter from `setup_impl`

## Context

This PR fixed a TypeError in `erk exec setup-impl --issue <N>` caused by passing an unsupported `branch_slug` parameter to `setup_impl_from_issue` via `ctx.invoke()`. The `--branch-slug` option was dead code that had been copy-pasted from another command without understanding its purpose. The bug manifested at runtime when Click's `ctx.invoke()` forwarded the keyword argument to a function that didn't accept it.

The implementation revealed several documentation gaps that will benefit future agents. Most significantly, parameter removal from Click commands requires a systematic 5-step verification process (the inverse of the existing parameter-addition-checklist.md), but this was not documented. Additionally, Click's `ctx.invoke()` has a non-obvious failure mode where parameter mismatches cause TypeError at runtime rather than at definition time.

The post-implementation workflow also demonstrated the complete PR review lifecycle, including batch thread resolution for duplicate automated review comments, validation with `erk pr check --stage=impl`, and the LBYL pattern for replacing `next()` without default value in test code.

## Raw Materials

PR #8130

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | 10    |
| Contradictions to resolve      | 0     |
| Tripwire candidates (score>=4) | 3     |
| Potential tripwires (score2-3) | 2     |

## Documentation Items

### HIGH Priority

#### 1. Parameter removal checklist

**Location:** `docs/learned/cli/parameter-removal-checklist.md`
**Action:** CREATE
**Source:** [Impl], [PR #8130]

**Draft Content:**

```markdown
# Parameter Removal Checklist

When removing a parameter from a Click command, verify all 5 locations:

## The 5-Step Verification

1. **CLI option declaration** - Remove `@click.option()` decorator
2. **Function signature** - Remove parameter from the command function
3. **All call sites** - Remove parameter from direct function calls
4. **Helper function signatures** - Remove from any helpers that forward the parameter
5. **ctx.invoke calls** - Remove from `ctx.invoke(target, ..., param=param)` calls

## Post-Removal Steps

After removing from all 5 locations, run `erk-dev gen-exec-reference-docs` to sync the CLI reference documentation.

## Common Failure Mode

Click's `ctx.invoke(function, **kwargs)` forwards keyword arguments directly. If a parameter is removed from the target function but not from the ctx.invoke call, you get a TypeError at runtime:

```
TypeError: target_function() got an unexpected keyword argument 'param_name'
```

See `src/erk/cli/commands/exec/scripts/setup_impl.py` for the fix pattern from PR #8130.

## Related

- See `docs/learned/cli/parameter-addition-checklist.md` for the inverse pattern
```

#### 2. ctx.invoke parameter mismatch detection

**Location:** `docs/learned/architecture/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8130]

**Draft Content:**

```markdown
## ctx.invoke Parameter Matching

**Before using ctx.invoke() with keyword arguments:**

Click's `ctx.invoke(function, **kwargs)` forwards keyword arguments directly to the target function. Any mismatch between kwargs and the function's signature causes TypeError at runtime, NOT at command definition time.

**Warning:** Verify all parameter names exactly match the target function's signature, including checking for recent parameter removals.

**Example failure:**
```python
# Target function
def setup_impl_from_issue(ctx, plan_number, session_id, no_impl): ...

# Caller - branch_slug was removed but not here
ctx.invoke(setup_impl_from_issue, ..., branch_slug=branch_slug)  # TypeError!
```

**Prevention:** When removing parameters, grep for `ctx.invoke.*function_name` to find all call sites.
```

#### 3. `.erk/impl-context/` cleanup requirement

**Location:** `docs/learned/planning/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## .erk/impl-context/ Cleanup

**Before running erk pr submit:**

The `.erk/impl-context/` directory MUST be removed before PR submission. This directory contains temporary context files used during implementation.

**Validation:** `erk pr check --stage=impl` validates this cleanup automatically and will fail if the directory is still present.

**Workflow:**
1. Run `erk pr submit`
2. Run `erk pr check --stage=impl`
3. If check fails: `git rm -r .erk/impl-context/` and commit
4. Re-run both commands
```

### MEDIUM Priority

#### 4. Self-triggering bug workflow

**Location:** `docs/learned/planning/self-triggering-bug-fixes.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# Self-Triggering Bug Fixes

When implementing a bug fix for `erk exec setup-impl` or similar core planning commands:

## The Paradox

The agent cannot run `setup-impl` to initialize `.impl/` because the command itself is broken. However, implementation can proceed immediately without workarounds.

## Why It Works

When a plan is saved via `erk exec plan-save`, it creates a branch and commits the `.impl/` folder. This means:

1. Plan is saved to GitHub issue
2. `plan-save` creates branch and commits `.impl/`
3. When implementing, `.impl/` is already present on the plan branch
4. Agent can implement the fix without needing to run the broken command

## Key Insight

The plan-save workflow creates implementation branches, so even if `setup-impl` is broken, the `.impl/` folder exists when implementing the fix. This is a non-obvious property of the plan-save pipeline that enables smooth bug fix workflows.

See PR #8130 for an example of this pattern in action.
```

#### 5. PR review lifecycle post-implementation

**Location:** `docs/learned/planning/pr-review-addressing-workflow.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# PR Review Addressing Workflow

Complete post-implementation workflow for addressing PR review comments.

## The 18-Step Lifecycle

### Phase 1: Implementation Completion
1. Run `make fast-ci` - all tests pass
2. Run `impl-signal ended` - signal implementation complete
3. Run `upload-impl-session` - upload session data
4. Run `impl-verify` - verify implementation artifacts

### Phase 2: Initial Submission
5. Run `erk pr submit` - create/update PR
6. Run `impl-signal submitted` - signal PR submitted
7. Run `erk pr check --stage=impl` - validate invariants

### Phase 3: Validation (if needed)
8. If check fails: fix the issue (e.g., remove `.erk/impl-context/`)
9. Commit the fix
10. Re-run `erk pr submit` and `erk pr check`

### Phase 4: Review Addressing
11. User triggers `/erk:pr-address` command
12. Load `pr-operations` skill for command reference
13. Classify feedback using `pr-feedback-classifier`
14. Display plan showing batched review threads
15. Address each batch (read files, make fixes, verify tests)
16. Commit changes for each batch
17. Resolve threads using `erk exec resolve-review-threads` with JSON stdin

### Phase 5: Completion
18. Push changes and update PR description with `erk exec update-pr-description --session-id`

## Batch Thread Resolution

When multiple review threads flag the same issue:

```bash
echo '[{"thread_id": "PRRT_abc", "comment": "..."}, {"thread_id": "PRRT_def", "comment": "..."}]' | erk exec resolve-review-threads
```
```

#### 6. Batch thread resolution workflow

**Location:** `docs/learned/pr-operations/batch-thread-resolution.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# Batch Thread Resolution

When resolving multiple PR review threads for the same fix, use the batch resolution pattern.

## JSON Stdin Pattern

```bash
echo '[
  {"thread_id": "PRRT_abc123", "comment": "Fixed by using LBYL pattern"},
  {"thread_id": "PRRT_def456", "comment": "Same fix addresses both comments"}
]' | erk exec resolve-review-threads
```

## When to Use

- Multiple automated bots flag the same issue (common with EAFP violations)
- Same code change addresses multiple review comments
- More efficient than individual `erk exec resolve-review-thread` calls

## Command Reference

See `erk exec resolve-review-threads --help` for full options.
```

#### 7. EAFP `next()` without default

**Location:** `docs/learned/testing/tripwires.md`
**Action:** UPDATE
**Source:** [Impl], [PR #8130]

**Draft Content:**

```markdown
## EAFP next() Without Default

**Before using next() on a generator or iterator in test code:**

Using `next()` without a default value is an EAFP anti-pattern. If the iterator is empty, you get `StopIteration` instead of a clear assertion message.

**Warning:** Use LBYL list check instead: `results = [x for x in ...]; assert results, 'Expected ...'; results[0]`

**Before (EAFP):**
```python
json_line = next(line for line in reversed(output_lines) if line.startswith("{"))
```

**After (LBYL):**
```python
json_lines = [line for line in reversed(output_lines) if line.startswith("{")]
assert json_lines, "Expected JSON output in command response"
json_line = json_lines[0]
```

**Why this matters:** Automated review bots flag this pattern. The LBYL version provides an explicit error message instead of an implicit `StopIteration`.
```

### LOW Priority

#### 8. `erk pr check --stage=impl` validation

**Location:** `docs/learned/pr-operations/pr-check-validation.md`
**Action:** CREATE
**Source:** [Impl]

**Draft Content:**

```markdown
# PR Check Validation

`erk pr check --stage=impl` validates invariants before considering a PR complete.

## Checks Performed

- `.erk/impl-context/` directory has been removed
- Implementation artifacts are properly cleaned up
- PR meets submission requirements

## Workflow

Always run after `erk pr submit`:

```bash
erk pr submit
erk pr check --stage=impl
```

If check fails, fix the violation and re-run both commands.

## Related

- See `docs/learned/planning/tripwires.md` for cleanup requirements
```

#### 9. Click option documentation generation

**Location:** `docs/learned/cli/tripwires.md`
**Action:** UPDATE
**Source:** [Impl]

**Draft Content:**

```markdown
## CLI Option Documentation Sync

**After modifying exec script CLI options:**

Run `erk-dev gen-exec-reference-docs` to regenerate `.claude/skills/erk-exec/reference.md`.

**Note:** `fast-ci` catches this automatically via the exec reference check. If fast-ci fails with "exec reference check", run the regeneration command.
```

#### 10. Automated bot review coordination

**Location:** `docs/learned/ci/automated-bot-review-coordination.md`
**Action:** CREATE
**Source:** [PR #8130]

**Draft Content:**

```markdown
# Automated Bot Review Coordination

Multiple automated bots review PRs and may flag the same issues.

## Bot Capabilities

- **Cross-file semantic analysis**: Bots can detect incomplete parameter removal by analyzing call sites across files
- **Inverse pattern detection**: Bots reference existing documentation (e.g., parameter-addition-checklist) to identify missing inverse patterns
- **EAFP detection**: Bots flag EAFP anti-patterns like `next()` without default

## Handling Duplicate Reviews

When multiple bots flag the same issue:
1. Fix the issue once
2. Resolve all threads in batch using `erk exec resolve-review-threads` with JSON stdin
3. Reference the same fix commit in each resolution comment

## Bot Review Lifecycle

1. PR created/updated
2. Bots analyze diff against loaded documentation
3. Bots post review comments on specific lines
4. Agent classifies and batches comments
5. Agent addresses each batch
6. Agent resolves threads
```

## Contradiction Resolutions

**No contradictions detected.** The existing documentation (parameter-threading-pattern.md, gateway-removal-pattern.md) aligns with the changes in this PR.

## Stale Documentation Cleanup

**No stale documentation detected.** ExistingDocsChecker verified that all referenced docs have valid file paths and no phantom references.

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. TypeError on ctx.invoke with unexpected keyword argument

**What happened:** `erk exec setup-impl --issue N` raised `TypeError: setup_impl_from_issue() got an unexpected keyword argument 'branch_slug'`

**Root cause:** Dead parameter was removed from target function `setup_impl_from_issue` but not from the `ctx.invoke()` call in `_handle_issue_setup`. Click's `ctx.invoke()` forwards kwargs directly to the target function.

**Prevention:** When removing parameters, search for ALL references including `ctx.invoke()` calls. Grep for `ctx.invoke.*function_name` to find call sites.

**Recommendation:** TRIPWIRE - Add to architecture tripwires

### 2. Parameter removal incomplete

**What happened:** The `--branch-slug` option was removed from `setup_impl` but not from all 5 locations that referenced it.

**Root cause:** No documented checklist for parameter removal (only parameter addition was documented).

**Prevention:** Follow the 5-step verification: (1) CLI option, (2) function signature, (3) call sites, (4) helper functions, (5) ctx.invoke calls. Then run `erk-dev gen-exec-reference-docs`.

**Recommendation:** TRIPWIRE - Create parameter-removal-checklist.md

### 3. `.erk/impl-context/` left after PR submission

**What happened:** `erk pr check --stage=impl` failed because the temporary context directory was still present.

**Root cause:** Agent didn't clean up the temporary context directory before submission.

**Prevention:** Always run `erk pr check --stage=impl` before considering PR complete. This check validates required cleanups.

**Recommendation:** ADD_TO_DOC - Update planning tripwires

### 4. EAFP next() without default in test code

**What happened:** Automated bots flagged `next(line for line in reversed(output_lines) if line.startswith("{"))` as EAFP violation.

**Root cause:** Test code used implicit exception instead of explicit check.

**Prevention:** Use list comprehension + assert for LBYL: `results = [x for x in ...]; assert results, "msg"; results[0]`

**Recommendation:** TRIPWIRE - Add to testing tripwires

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. Parameter removal checklist

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Repeated pattern +1, Silent failure potential +1)

**Trigger:** Before removing a parameter from a Click command

**Warning:** Follow 5-step verification: (1) CLI option, (2) function signature, (3) all call sites, (4) helper functions, (5) ctx.invoke calls. Then run `erk-dev gen-exec-reference-docs`.

**Target doc:** `docs/learned/cli/tripwires.md`

This is tripwire-worthy because the bug in this PR was caused by incomplete parameter removal. The inverse pattern (parameter addition) is already documented, but removal requires the same systematic verification. Without this tripwire, agents will make the same mistake of partially removing parameters and leaving dead references in ctx.invoke calls.

### 2. ctx.invoke parameter mismatch detection

**Score:** 6/10 (Non-obvious +2, Cross-cutting +2, Silent failure potential +2)

**Trigger:** Before using ctx.invoke() with keyword arguments

**Warning:** Verify all parameter names exactly match the target function's signature, including checking for recent parameter removals. Click forwards kwargs directly - any mismatch causes TypeError at runtime.

**Target doc:** `docs/learned/architecture/tripwires.md`

This is tripwire-worthy because the error happens at runtime, not when the command is defined. There's no static type checking or linting that catches this. Any command using ctx.invoke() with keyword arguments is vulnerable to this failure mode when target function signatures change.

### 3. EAFP next() without default

**Score:** 4/10 (Non-obvious +2, Repeated pattern +1, External tool quirk +1)

**Trigger:** Before using next() on a generator or iterator in test code

**Warning:** Use LBYL list check instead: `results = [x for x in ...]; assert results, 'Expected ...'; results[0]`

**Target doc:** `docs/learned/testing/tripwires.md`

This is tripwire-worthy because automated review bots explicitly flag this pattern. It's a common EAFP violation that violates erk's LBYL-everywhere policy. The StopIteration exception is less clear than an explicit assertion message.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. Click option documentation generation

**Score:** 3/10 (Cross-cutting +2, External tool quirk +1)

**Notes:** fast-ci catches this automatically via the exec reference check, so it's not a silent failure. However, it's a repeated pattern across CLI changes. Could be promoted if agents repeatedly fail this check.

### 2. `.erk/impl-context/` cleanup

**Score:** 3/10 (Cross-cutting +2, Destructive potential +1)

**Notes:** `erk pr check --stage=impl` catches this automatically, so it's not a silent failure. But it's important enough to know proactively. Already added to planning tripwires as a lower-priority note.
