---
title: Gateway Signature Migration
read_when:
  - "changing gateway method signatures"
  - "migrating callers after gateway API changes"
  - "updating discriminated union return types across call sites"
tripwires:
  - action: "changing a gateway method signature"
    warning: "Search for ALL callers with grep before changing. PR #6329 migrated 8 call sites across 7 files. Missing a call site causes runtime errors."
---

# Gateway Signature Migration

When changing a gateway method signature (especially return types), you must update every implementation and every caller. The gateway's 5-file pattern magnifies the impact—a single method change touches at least 5 files, and typically many more when callers are updated.

## Why This Is Hard

Gateway methods are called from many locations across packages. Unlike single-file refactorings where the IDE finds all usages, gateway changes involve:

1. **Cross-package call sites** — `packages/erk-shared/` gateways called from `src/erk/`
2. **Multiple implementation variants** — abc, real, fake, dry_run, printing
3. **Test fixtures and helpers** — tests often construct gateway calls indirectly
4. **Type checker limitations** — changing the ABC doesn't automatically flag all call sites

The type checker will find missing implementations when you change the ABC, but it won't necessarily flag all callers that need to handle the new return type differently.

## The Systematic Approach

### Step 1: Discover All Call Sites Before Changing Anything

Use grep to find every reference to the method across ALL packages:

```bash
grep -rn "method_name" src/ packages/ tests/
```

**Count and record every location.** In PR #6329, this search revealed 8 call sites across 7 files for `push_to_remote` and `pull_rebase`.

**Why this matters:** You're about to break all these call sites. Knowing the full scope up front prevents discovering missed callers during CI runs or (worse) production.

### Step 2: Update the ABC First

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/abc.py, push_to_remote, pull_rebase -->

Change the abstract method signature in the gateway's `abc.py`. This is your anchor point—the type checker will now flag all 4 remaining implementations (real, fake, dry_run, printing) as incomplete.

See `push_to_remote()` and `pull_rebase()` in `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/abc.py` for examples of methods that return discriminated unions.

**Why ABC first:** The type checker becomes your assistant. Each implementation that doesn't match the new signature shows up as an error.

### Step 3: Update All 5 Implementations in Order

Work through each implementation systematically:

1. **`abc.py`** — Already done (Step 2)
2. **`real.py`** — Production behavior (subprocess calls, API requests)
3. **`fake.py`** — Test double behavior (constructor parameters, mutation tracking)
4. **`dry_run.py`** — Preview behavior (no-op for mutations, delegate for reads)
5. **`printing.py`** — Verbose behavior (log and delegate)

Each file must match the ABC signature exactly. The type checker will guide you through real, fake, and dry_run. Printing implementations often fall behind—don't forget them.

### Step 4: Migrate Every Caller

Return to your Step 1 list and update every call site. For discriminated union changes, this means:

- **Remove try/except blocks** around the call
- **Add isinstance() checks** for the error variant
- **Update error handling** to use `.message` property or structured error fields

<!-- Source: src/erk/cli/commands/pr/submit_pipeline.py, handle push and pull-rebase errors -->

See `src/erk/cli/commands/pr/submit_pipeline.py` for examples of migrated callers that check `isinstance(result, PushError)`.

**Common mistake:** Forgetting test helpers that construct calls indirectly. Grep finds method invocations, but constructor parameters for fakes (`push_to_remote_error=...`) require additional inspection.

### Step 5: Verify with Type Checker and Grep

Run the type checker across all packages:

```bash
ty check src/ packages/
```

Grep again to confirm no old patterns remain:

```bash
grep -rn "old_pattern_or_parameter" src/ packages/
```

If you're removing a parameter, grep for the parameter name. If you're changing exception handling, grep for the exception type.

## The PR #6329 Case Study

PR #6329 converted `push_to_remote` and `pull_rebase` from exception-based error handling to discriminated unions (`PushResult | PushError`, `PullRebaseResult | PullRebaseError`).

**Scope:**

- **5 gateway implementations** (abc, real, fake, dry_run, printing)
- **8 call sites** across **7 files**
- **New types module** (`remote_ops/types.py`) with 4 new frozen dataclasses

<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py, PushResult, PushError, PullRebaseResult, PullRebaseError -->

See `packages/erk-shared/src/erk_shared/gateway/git/remote_ops/types.py` for the discriminated union types defined for this migration.

**Key insight:** All callers previously used try/except blocks. The migration required converting each to isinstance checks and extracting error messages from the `.message` property instead of `str(e)`.

**Test changes:** 3 test files updated from `push_to_remote_raises=RuntimeError(...)` pattern to `push_to_remote_error=PushError(...)`.

## What Makes Signature Changes Safe

1. **Grep before, grep after** — Know the full scope before starting; verify nothing was missed after finishing
2. **Type checker as guardrail** — Let it find implementation mismatches for you
3. **Run the full test suite** — Test helpers and fixtures reveal indirect callers
4. **Cross-package awareness** — Search both `src/erk/` and `packages/` directories

## When to Split the Migration

For very large changes (10+ call sites), consider a two-PR approach:

1. **PR 1:** Add the new signature as an optional variant (e.g., new method name or optional parameter)
2. **PR 2:** Migrate all callers and remove the old signature

This keeps each PR focused and testable. However, for gateway ABCs where the 5-file pattern already constrains you, doing it atomically in one PR is often cleaner.

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — The 5-place pattern for all gateway changes
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — Why and when to use return unions instead of exceptions
