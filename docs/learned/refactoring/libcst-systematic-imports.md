---
title: LibCST Systematic Import Refactoring
last_audited: "2026-02-08"
audit_result: regenerated
read_when:
  - "refactoring imports across many files"
  - "renaming modules or packages"
  - "deciding between manual edits and automated refactoring"
tripwires:
  - action: "manually updating imports across 10+ files"
    warning: "Use LibCST via the libcst-refactor agent or a one-off script. Manual editing misses call sites and creates partial migration states."
  - action: "writing LibCST transformation logic from scratch"
    warning: "The libcst-refactor agent (.claude/agents/libcst-refactor.md) contains battle-tested patterns, gotchas, and a script template. Load it first."
  - action: "interleaving file moves and import updates"
    warning: "Move ALL files first (git mv), THEN batch-update ALL imports. Interleaving creates intermediate broken states. See gateway-consolidation-checklist.md."
---

# LibCST Systematic Import Refactoring

## When to Use LibCST

LibCST parses Python source into a concrete syntax tree that preserves formatting and comments, making it ideal for mechanical import refactoring. The key question is whether the transformation is worth the tooling overhead.

| Situation | Approach | Why |
| --- | --- | --- |
| 1-3 files need import changes | Manual Edit tool | Faster than writing a transformer; review is trivial |
| 4-9 files, simple rename | Edit tool with `replace_all` | Still mechanical but not enough files to justify a script |
| 10+ files, import path change | `libcst-refactor` agent | Systematic replacement prevents missed call sites |
| ABC consolidation (type renames + import moves + field renames) | `libcst-refactor` agent | Multiple transformation types across 40+ files; manual editing is error-prone |
| Non-Python files (YAML, markdown, configs) | Grep + manual or sed | LibCST only handles Python |

**The crossover point is ~10 files.** Below that, the time to write and test a transformer exceeds the time to make manual edits. Above that, manual editing becomes the riskier option because missed call sites cause runtime `ImportError`s that may not surface until a specific code path executes.

## The Erk Workflow

LibCST fits into a specific phase of erk's refactoring workflow. The ordering matters — doing these out of sequence creates intermediate broken states where some imports reference old paths and others reference new ones.

<!-- Source: docs/learned/planning/gateway-consolidation-checklist.md -->

The gateway consolidation checklist documents the full phase ordering. The critical constraint: **move all files before updating any imports**, so that all old→new path mappings are known when the LibCST pass runs.

### Phase Integration

1. **`git mv`** all source files to their new locations
2. **LibCST pass** — one transformer handles all import remappings in a single run
3. **`ruff check --fix`** — fixes import sorting violations (I001) caused by changed paths
4. **Full test suite** — catches any imports the transformer missed

The LibCST pass is a single operation, not a file-by-file edit. This is the key advantage: the transformer processes every Python file, applies all remappings, and reports which files changed. No call site can be missed unless it's in a non-Python file.

## Using the libcst-refactor Agent

<!-- Source: .claude/agents/libcst-refactor.md -->

The `libcst-refactor` agent (invoked via `Task(subagent_type='libcst-refactor')`) contains the complete LibCST reference: 6 critical success principles, 11 transformation patterns, 5 gotchas with solutions, debugging techniques, and a battle-tested script template. The agent creates ephemeral refactoring scripts, runs them, and reports results.

**Do not duplicate the agent's content in conversation or plans.** Invoke it with a clear description of the transformation needed. The agent is context-isolated — it doesn't see your conversation history, so include:

- The old import path(s) and new import path(s)
- Which directories to scan (`src/`, `packages/`, `tests/`)
- Any type renames (e.g., `ClaudeExecutor` → `PromptExecutor`)
- Any field/attribute renames (e.g., `ctx.claude_executor` → `ctx.prompt_executor`)

## Lessons from Past Refactorings

### ABC Consolidation Requires Multi-Layer Transformation

Simple import-path changes only need `leave_ImportFrom`. But consolidating one ABC into another (e.g., merging `ClaudeExecutor` into `PromptExecutor`) requires three transformation layers in a single pass:

1. **Import paths** — `leave_ImportFrom` to remap module paths
2. **Type names** — `leave_Name` to rename class references throughout
3. **Attribute access** — `leave_Attribute` to rename context fields like `ctx.old_name` → `ctx.new_name`

Running these as separate passes risks inconsistency — a file could have the new import path but the old type name. A single `CSTTransformer` class with all three `leave_*` methods ensures atomicity per file.

### Partial Path Matching Is the Most Common Bug

A matcher for `erk_shared.gateway` will also match `erk_shared.gateway.git`. The fix is to match the complete module path, not just a prefix. When writing matchers for deeply nested import paths, the nested `m.Attribute()` structure is verbose but necessary — each level must be explicit.

### Relative Imports Should Be Skipped

Transformers that update absolute import paths must not touch relative imports (`.abc`, `.types`). Relative imports are internal to the moved package and remain correct after the move. Guard against this early:

```python
# Skip relative imports — they're internal to the package
if updated_node.relative:
    return updated_node
```

This is one of the four permitted code block exceptions (third-party API pattern — teaching LibCST's `relative` attribute).

### Type Name Renames Need Scope Guards

A naive `leave_Name` that renames "Claude" to "Prompt" will also rename user-facing strings containing "Claude". Scope the rename to exact class/type names, and use a whitelist dictionary rather than substring matching.

## Related Documentation

- [Gateway Consolidation Checklist](../planning/gateway-consolidation-checklist.md) — the full refactoring workflow that LibCST plugs into
- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — the 5-place pattern that must be updated during consolidation
- [Re-Export Pattern](../architecture/re-export-pattern.md) — temporary re-exports during migration, cleaned up after LibCST pass
