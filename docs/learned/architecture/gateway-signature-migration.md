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

A systematic pattern for updating all call sites when a gateway method signature changes. This is critical because gateway methods are called from many locations across packages.

## The Pattern

### Step 1: Identify All Call Sites

```bash
# Search across ALL packages for the method name
grep -rn "push_to_remote\|pull_rebase" src/ packages/ tests/
```

Count and record every call site before changing anything.

### Step 2: Update the ABC

Change the abstract method signature in `abc.py`. This makes the type checker flag all 4 remaining implementations.

### Step 3: Update All 5 Implementations

Update in order:

1. `abc.py` — New signature (already done)
2. `real.py` — Production behavior
3. `fake.py` — Test double behavior
4. `dry_run.py` — Preview behavior
5. `printing.py` — Verbose behavior

### Step 4: Migrate All Callers

Update every call site found in Step 1 to use the new signature. For discriminated union changes, update all `isinstance()` checks.

### Step 5: Verify

```bash
# Type check across packages
ty check src/ packages/

# Grep again to confirm no old patterns remain
grep -rn "old_pattern" src/ packages/
```

## Reference: PR #6329

PR #6329 converted `push_to_remote` and `pull_rebase` from raising exceptions to returning discriminated unions. The migration touched:

- **8 call sites** across **7 files**
- 5 gateway implementations (abc, real, fake, dry_run, printing)
- Updated all callers from try/except to isinstance() checks

## Key Lessons

1. **Grep first**: Always discover all callers before starting the migration
2. **Type checker is your friend**: Changing the ABC first makes the type checker find implementation mismatches
3. **Tests reveal callers too**: Run the full test suite — test helpers and fixtures often call gateway methods
4. **Cross-package awareness**: Gateway methods in `packages/erk-shared/` are called from `src/erk/` — search both

## Related Documentation

- [Gateway ABC Implementation Checklist](gateway-abc-implementation.md) — The 5-place pattern
- [Discriminated Union Error Handling](discriminated-union-error-handling.md) — The return type pattern
