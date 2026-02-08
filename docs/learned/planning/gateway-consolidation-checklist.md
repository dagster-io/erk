---
title: Gateway Consolidation Checklist
last_audited: "2026-02-08"
audit_result: edited
read_when:
  - "moving a gateway package into the gateway/ directory"
  - "extracting a new gateway from existing code"
  - "performing large-scale import refactoring across packages"
tripwires:
  - action: "moving gateway files without git mv"
    warning: "Always use git mv to preserve file history. Plain mv + git add loses blame history, making future archaeology harder."
  - action: "updating imports one file at a time during gateway consolidation"
    warning: "Use LibCST for systematic import updates. Manual editing misses call sites and creates partial migration states. See docs/learned/refactoring/libcst-systematic-imports.md."
  - action: "renaming gateway files during a move without checking for non-standard naming"
    warning: "Source files that don't follow standard naming (e.g., executor.py instead of abc.py) must be renamed to abc.py/real.py/fake.py during the move. The gateway directory convention requires standard file names."
---

# Gateway Consolidation Checklist

## Context

All gateway packages live under `packages/erk-shared/src/erk_shared/gateway/`. This was not always the case — gateways were originally scattered across domain-specific directories (e.g., TUI commands, CLI utilities). Consolidation into a single `gateway/` tree was done because:

1. **Discoverability** — agents searching for "where is the X gateway?" need one place to look, not a codebase-wide search
2. **Consistency enforcement** — the 5-file pattern (abc/real/fake/dry_run/printing) is easier to verify when all gateways are siblings
3. **Import predictability** — `erk_shared.gateway.<name>.abc` is a mechanical derivation from the gateway name, eliminating guesswork

There are currently 27 gateway packages in this directory. Some use the full 5-file pattern, others use a simplified 3-file pattern (no dry_run/printing). Complex domains (Git, GitHub, Graphite) use nested sub-gateways.

## Operation Ordering: Why It Matters

The single most important insight from past consolidation work: **move all files before updating any imports**.

| Phase | What | Why |
|-------|------|-----|
| 1. Move files | `git mv` all sources to new locations | Preserves git history; creates a codebase that won't compile but has correct file layout |
| 2. Update imports | LibCST batch transformation | All old→new path mappings are known; systematic replacement prevents missed call sites |
| 3. Lint fix | `ruff check --fix` across affected directories | Import sorting violations (I001) are inevitable after bulk moves; fix once at the end |
| 4. Test | Full test suite | Catches any missed import sites or broken circular dependencies |

**Anti-pattern: interleaving moves and import updates.** Moving gateway A, fixing its imports, then moving gateway B creates intermediate broken states where gateway A's imports reference the new location but gateway B's cross-references still point to the old one. Batch all moves first, then batch all import updates.

## Non-Obvious Pitfalls

### File Naming Normalization

Scattered gateways often have domain-specific file names (e.g., `executor.py` for the ABC, `real_executor.py` for the real implementation). During the move, these must be renamed to the standard `abc.py`/`real.py`/`fake.py` convention. This is a rename-during-move — `git mv old_path/executor.py new_path/abc.py` handles both operations atomically.

### Circular Imports After Consolidation

Moving gateways into sibling directories can surface circular imports that were previously hidden by package boundaries. The symptom is `ImportError: cannot import name 'X' from partially initialized module`.

The root cause is usually a gateway ABC that imports types from another gateway. The fix is a `TYPE_CHECKING` guard — these imports are only needed for type annotations, not runtime behavior. This is one of the few places where erk uses `TYPE_CHECKING` (normally erk avoids it because LBYL patterns need runtime types).

### Empty `__init__.py` with Docstring

Per erk's no-re-exports convention, `__init__.py` files must be empty of executable code. But they should include a docstring listing the submodules and their key symbols. This acts as a human-readable index without creating import shortcuts that hide the canonical import path.

## Batch vs Single-Gateway Consolidation

| Approach | When to use | Trade-off |
|----------|------------|-----------|
| **Single gateway** | Gateway has few import sites (<10) | Simpler PR, easier review, but overhead per gateway is high |
| **Batch (multiple gateways)** | Consolidating 3+ related gateways | One LibCST pass handles all remappings; one lint fix; one test run. But PR is larger and harder to review |

For batch operations, LibCST is nearly mandatory — manual import updates across dozens of files are error-prone and slow.

<!-- Source: docs/learned/refactoring/libcst-systematic-imports.md -->

See [LibCST Systematic Imports](../refactoring/libcst-systematic-imports.md) for the transformer pattern and step-by-step workflow.

## Post-Move Checklist

After moving files and updating imports, these steps are easy to forget:

1. **Update gateway inventory** — add the new entry to the gateway inventory doc
2. **Update any doc referencing old paths** — grep `docs/learned/` for the old import path
3. **Verify the `__init__.py`** exists in the new directory — missing it produces `ModuleNotFoundError` that looks like a bad import rather than a missing file

<!-- Source: docs/learned/architecture/gateway-inventory.md -->
<!-- Source: docs/learned/architecture/gateway-abc-implementation.md -->

## Related Documentation

- [Gateway Inventory](../architecture/gateway-inventory.md) — current catalog of all gateway packages
- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — the 5-place implementation pattern that consolidated gateways must follow
- [LibCST Systematic Imports](../refactoring/libcst-systematic-imports.md) — automated import refactoring for batch moves
