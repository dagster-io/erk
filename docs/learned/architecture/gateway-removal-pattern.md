---
title: Gateway Removal Pattern
last_audited: "2026-02-15"
audit_result: clean
tripwires:
  - action: "deleting a gateway after consolidating into another"
    warning: "Follow complete removal checklist: verify no references, delete all 5 layers, clean up compositions, update docs, run full test suite."
read_when:
  - "Consolidating two gateways into one"
  - "Removing deprecated gateway implementations"
  - "Refactoring gateway hierarchies"
---

# Gateway Removal Pattern

## When to Remove a Gateway

Gateway removal follows successful consolidation — when one gateway's functionality has been merged into another and all callers have migrated. Erk's unreleased status means no backward compatibility: deprecated gateways are deleted immediately, not marked for future removal.

**Preconditions for safe removal:**

1. **Zero production references** — No imports, type annotations, or instantiations in `src/erk/` or `packages/erk-shared/`
2. **Functionality absorbed** — The target gateway provides all capabilities of the deprecated gateway
3. **Test coverage migrated** — Old gateway's test scenarios now covered by target gateway's tests
4. **No external dependents** — Erk is private software with no external users

## Why Immediate Deletion

Erk deliberately avoids the deprecation-grace-period pattern common in public libraries:

**No deprecation warnings** — The old gateway vanishes atomically in a single PR. Callers that haven't migrated fail loudly at type check time, not silently at runtime with warnings.

**No legacy shims** — No adapter layer mapping old method signatures to new ones. Migration is mandatory, not optional.

**No version compatibility** — Erk breaks forward compatibility freely. Code written against one commit may not work against the next.

**Trade-off accepted:** This creates migration burden (all callers must update simultaneously), but eliminates maintenance burden (zero dead code in the repository). For a private tool with a single-team user base, this is the correct trade.

## Complete Removal Checklist

### 1. Verify Zero References

Search for all forms of usage across the codebase:

```bash
# Direct imports
rg "from.*GatewayName|import.*GatewayName"

# Type annotations
rg ":\s*GatewayName"

# Instantiation
rg "GatewayName\("

# Property access (if gateway was composed)
rg "\.gateway_name"
```

Zero matches across all patterns required before proceeding. Even a single reference blocks removal — the gateway cannot be partially deleted.

### 2. Delete Implementation Files

Remove all 5 gateway layers in one commit:

```bash
git rm -rf src/erk/gateway/gateway_name/
# Or for shared gateways:
git rm -rf packages/erk-shared/src/erk_shared/gateway/gateway_name/
```

**Why delete the entire directory:** Leaves no orphaned `__init__.py` files or empty package structure. The gateway ceases to exist at the package level.

### 3. Delete Test Files

Remove corresponding test suite:

```bash
git rm -rf tests/unit/gateway/gateway_name/
git rm -rf tests/integration/test_real_gateway_name.py
```

**Critical verification:** Before deletion, confirm the target gateway's tests provide equivalent coverage. The migration should preserve test scenarios, not discard them.

### 4. Remove Gateway Compositions

If the deleted gateway was composed into parent gateways (e.g., a subgateway property on Git or GitHub), remove the composition from **all 5 parent layers:**

**ABC layer:**

- Delete `@property @abstractmethod` definition
- Remove TYPE_CHECKING import

**Real layer:**

- Remove constructor parameter
- Delete `self._gateway = ...` initialization
- Remove property returning the gateway

**Fake layer:**

- Remove constructor parameters for both test data and gateway injection
- Delete property returning fake gateway
- Remove any state linking calls (`link_mutation_tracking`, etc.)

**DryRun layer:**

- Delete property wrapping the subgateway

**Printing layer:**

- Delete property wrapping the subgateway

**Why 5-place removal:** Partial removal causes type checker errors. If the ABC still declares the property but Real doesn't implement it, `ty` reports an unimplemented abstract method. All layers must change atomically.

### 5. Update Documentation

- Remove gateway from `docs/learned/architecture/` if documented
- Delete any gateway-specific guides or patterns
- Note removal in next changelog update (via `/local:changelog-update` after merging)

**Do not mention migration** — There's no future where users need to know about the old gateway. Document the current state (target gateway's API), not the historical transition.

### 6. Verify with Full Test Suite

```bash
make test-unit
make test-integration
ty  # Type checker
```

**Zero failures required.** Any failure indicates missed references or incomplete cleanup.

## Example: ClaudeExecutor → PromptExecutor (PR #6587)

Consolidation rationale: ClaudeExecutor and PromptExecutor performed the same function (launching Claude agent processes) with slightly different APIs. The merged PromptExecutor combined both capabilities.

**Removal steps executed:**

1. **Migration phase** (separate PR) — All 7 call sites updated to use `PromptExecutor`
2. **Verification** — `rg "ClaudeExecutor"` returned zero matches in production code
3. **Layer deletion** — Removed `src/erk/gateway/claude_executor/` containing abc.py, real.py, fake.py, dry_run.py, printing.py
4. **Test deletion** — Removed `tests/unit/gateway/claude_executor/`
5. **Composition removal** — Deleted `claude_executor` property from ErkContext ABC and all 5 implementations
6. **Test verification** — `make test-unit` passed with zero failures

**Outcome:** 200+ lines of code deleted, one clear path to launch agents remains.

## Anti-Patterns

### Keeping "just the ABC for reference"

**Symptom:** Real/Fake/DryRun/Printing deleted, but ABC left with a "this is deprecated" comment.

**Why wrong:** Creates import ghosts — the ABC is still importable, so callers can write code that type-checks but fails at runtime when they try to instantiate. Abstractions without implementations are dead code.

**Correct approach:** Delete the ABC with the implementations. Git history preserves the old interface for archaeology.

### Leaving empty package directories

**Symptom:** `gateway/old_gateway/` directory still exists with an empty `__init__.py` after file removal.

**Why wrong:** Empty packages clutter import namespaces and confuse grep searches ("the directory exists, so maybe something uses it").

**Correct approach:** `git rm -rf` removes the directory atomically. No empty structure remains.

### Commenting out instead of deleting

**Symptom:** Gateway code replaced with block comments preserving the old implementation "just in case."

**Why wrong:** Comments aren't under test, go stale immediately, and add noise to file reading. Git blame already provides archaeology.

**Correct approach:** Hard delete. Use `git log -p --all -S "OldGatewayName"` to recover old implementation if truly needed.

### Partial composition removal

**Symptom:** Property deleted from ABC and Real, but Fake still has a `gateway_name` property returning `None`.

**Why wrong:** Type checker won't catch this until a test actually accesses the property. Tests pass accidentally (not exercising the deleted path), then fail later when someone adds a test that does.

**Correct approach:** Remove from all 5 layers in a single commit. Incomplete removal is worse than no removal (half-deleted state is confusing).

## Decision Framework

**When consolidating two similar gateways, which should survive?**

| Criterion                                              | Prefer this gateway |
| ------------------------------------------------------ | ------------------- |
| More comprehensive API                                 | Keep                |
| More callers using it                                  | Keep                |
| Cleaner implementation                                 | Keep                |
| Better aligned with discriminated union error handling | Keep                |
| Newer code with less tech debt                         | Keep                |

**No clear winner?** Pick arbitrarily, migrate, delete. The choice matters less than eliminating duplication. Merge the best features from both into the survivor.

## Maintenance Burden Elimination

Gateway removal is part of erk's broader "no legacy code" philosophy:

**When code becomes redundant, delete it the same day.** Don't let deprecated gateways linger for "just one release" or "until we're sure the migration worked." The test suite provides certainty; passing tests mean the migration succeeded.

**Cost of keeping dead code:**

- False positives in grep searches (have to check if references are production or legacy)
- Maintenance updates (when signature patterns change, dead code needs updates too)
- Confusion for future developers ("why do we have two ways to do this?")
- Larger cognitive surface area (more concepts to hold in working memory)

**Cost of removing too aggressively:**

- Type checker errors if you missed a reference (caught immediately, fixed in minutes)
- Need to resurrect from git history (rare, takes 5 minutes)

The error asymmetry heavily favors aggressive deletion.

## Related Documentation

- [Gateway ABC Implementation](gateway-abc-implementation.md) — 5-layer pattern that gateway removal must fully unwind
- [Flatten Subgateway Pattern](flatten-subgateway-pattern.md) — Property-based composition that must be deleted when removing subgateways
