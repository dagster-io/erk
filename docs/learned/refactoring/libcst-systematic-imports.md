---
title: LibCST Systematic Import Refactoring
last_audited: "2026-02-16 02:45 PT"
audit_result: clean
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
  - action: "running targeted edits after replace_all operations in the same file"
    warning: "During type migrations, complete all rename operations before attempting targeted edits. replace_all operations change strings that later edits expect to find."
---

# LibCST Systematic Import Refactoring

## When to Use LibCST

LibCST parses Python source into a concrete syntax tree that preserves formatting and comments, making it ideal for mechanical import refactoring. The key question is whether the transformation is worth the tooling overhead.

| Situation                                                       | Approach                     | Why                                                                           |
| --------------------------------------------------------------- | ---------------------------- | ----------------------------------------------------------------------------- |
| 1-3 files need import changes                                   | Manual Edit tool             | Faster than writing a transformer; review is trivial                          |
| 4-9 files, simple rename                                        | Edit tool with `replace_all` | Still mechanical but not enough files to justify a script                     |
| 10+ files, import path change                                   | `libcst-refactor` agent      | Systematic replacement prevents missed call sites                             |
| ABC consolidation (type renames + import moves + field renames) | `libcst-refactor` agent      | Multiple transformation types across 40+ files; manual editing is error-prone |
| Non-Python files (YAML, markdown, configs)                      | Grep + manual or sed         | LibCST only handles Python                                                    |

**The crossover point is ~10 files.** Below that, the time to write and test a transformer exceeds the time to make manual edits. Above that, manual editing becomes the riskier option because missed call sites cause runtime `ImportError`s that may not surface until a specific code path executes.

## Installation

LibCST is included in erk's dev dependencies:

```bash
uv sync --dev
```

## The Erk Workflow

LibCST fits into a specific phase of erk's refactoring workflow. The ordering matters — doing these out of sequence creates intermediate broken states where some imports reference old paths and others reference new ones.

<!-- Source: docs/learned/planning/gateway-consolidation-checklist.md -->

The gateway consolidation checklist documents the full phase ordering. The critical constraint: **move all files before updating any imports**, so that all old->new path mappings are known when the LibCST pass runs.

### Phase Integration

1. **`git mv`** all source files to their new locations
2. **LibCST pass** — one transformer handles all import remappings in a single run
3. **`ruff check --fix`** — fixes import sorting violations (I001) caused by changed paths
4. **Full test suite** — catches any imports the transformer missed

The LibCST pass is a single operation, not a file-by-file edit. This is the key advantage: the transformer processes every Python file, applies all remappings, and reports which files changed. No call site can be missed unless it's in a non-Python file.

## Transformer Template

A complete transformer script showing the standard pattern:

```python
"""Refactor imports to new path."""

import libcst as cst
from libcst import matchers as m


class ImportTransformer(cst.CSTTransformer):
    """Transform imports to new location."""

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform import statements."""
        # Skip relative imports — they're internal to the package
        if updated_node.relative:
            return updated_node

        # Match: from erk_shared.tui.commands.executor import ...
        if m.matches(
            updated_node,
            m.ImportFrom(
                module=m.Attribute(
                    value=m.Attribute(
                        value=m.Attribute(
                            value=m.Name("erk_shared"),
                            attr=m.Name("tui"),
                        ),
                        attr=m.Name("commands"),
                    ),
                    attr=m.Name("executor"),
                )
            ),
        ):
            # Replace with: from erk_shared.gateway.command_executor import ...
            return updated_node.with_changes(
                module=cst.Attribute(
                    value=cst.Attribute(
                        value=cst.Name("erk_shared"),
                        attr=cst.Name("gateway"),
                    ),
                    attr=cst.Name("command_executor"),
                )
            )

        return updated_node


if __name__ == "__main__":
    import sys
    from pathlib import Path

    # Read input
    source_code = sys.stdin.read()

    # Parse and transform
    module = cst.parse_module(source_code)
    transformed = module.visit(ImportTransformer())

    # Write output
    print(transformed.code, end="")
```

### Applying the Transformer

```bash
# Find files with old imports
files=$(grep -rl "from erk_shared.tui.commands.executor" packages/ src/)

# Apply transformation
for file in $files; do
    python scripts/refactor_imports.py < "$file" > "$file.tmp"
    mv "$file.tmp" "$file"
done

# Fix import sorting
ruff check --fix packages/ src/
```

## LibCST Matcher Pattern Library

LibCST uses matchers to identify AST nodes. Common patterns for import refactoring:

### Import From Module

```python
# Match: from foo.bar import baz
m.ImportFrom(
    module=m.Attribute(
        value=m.Name("foo"),
        attr=m.Name("bar"),
    )
)
```

### Import From with Alias

```python
# Match: from foo import bar as baz
m.ImportFrom(
    names=[
        m.ImportAlias(
            name=m.Name("bar"),
            asname=m.AsName(name=m.Name("baz")),
        )
    ]
)
```

### Deeply Nested Module Path

```python
# Match: from erk_shared.tui.commands.executor import ...
m.ImportFrom(
    module=m.Attribute(
        value=m.Attribute(
            value=m.Attribute(
                value=m.Name("erk_shared"),
                attr=m.Name("tui"),
            ),
            attr=m.Name("commands"),
        ),
        attr=m.Name("executor"),
    )
)
```

### Function Call on Object

```python
# Match: ctx.git.branch.create_branch()
m.Call(
    func=m.Attribute(
        value=m.Attribute(
            value=m.Attribute(value=m.Name("ctx"), attr=m.Name("git")),
            attr=m.Name("branch"),
        ),
        attr=m.Name("create_branch"),
    )
)
```

### Attribute Access

```python
# Match: ctx.claude_executor
m.Attribute(
    value=m.Name("ctx"),
    attr=m.Name("claude_executor"),
)
```

## Using the libcst-refactor Agent

<!-- Source: .claude/agents/libcst-refactor.md -->

The `libcst-refactor` agent (invoked via `Task(subagent_type='libcst-refactor')`) contains the complete LibCST reference: 6 critical success principles, 11 transformation patterns, 5 gotchas with solutions, debugging techniques, and a battle-tested script template. The agent creates ephemeral refactoring scripts, runs them, and reports results.

**Do not duplicate the agent's content in conversation or plans.** Invoke it with a clear description of the transformation needed. The agent is context-isolated — it doesn't see your conversation history, so include:

- The old import path(s) and new import path(s)
- Which directories to scan (`src/`, `packages/`, `tests/`)
- Any type renames (e.g., `ClaudeExecutor` -> `PromptExecutor`)
- Any field/attribute renames (e.g., `ctx.claude_executor` -> `ctx.prompt_executor`)

## Lessons from Past Refactorings

### ABC Consolidation Requires Multi-Layer Transformation

Simple import-path changes only need `leave_ImportFrom`. But consolidating one ABC into another (e.g., merging `ClaudeExecutor` into `PromptExecutor`) requires three transformation layers in a single pass:

1. **Import paths** — `leave_ImportFrom` to remap module paths
2. **Type names** — `leave_Name` to rename class references throughout
3. **Attribute access** — `leave_Attribute` to rename context fields like `ctx.old_name` -> `ctx.new_name`

Running these as separate passes risks inconsistency — a file could have the new import path but the old type name. A single `CSTTransformer` class with all three `leave_*` methods ensures atomicity per file.

#### ABC Consolidation Transformer Example

**Step 1: Import path updates**

```python
class PromptExecutorConsolidationTransformer(cst.CSTTransformer):
    def leave_ImportFrom(self, original_node, updated_node):
        if updated_node.relative:
            return updated_node
        # Match: from erk_shared.core.claude_executor import ...
        # Replace with: from erk_shared.core.prompt_executor import ...
        if m.matches(updated_node, m.ImportFrom(module=m.Attribute(
            value=m.Attribute(value=m.Name("erk_shared"), attr=m.Name("core")),
            attr=m.Name("claude_executor")
        ))):
            return updated_node.with_changes(
                module=cst.Attribute(
                    value=cst.Attribute(value=cst.Name("erk_shared"), attr=cst.Name("core")),
                    attr=cst.Name("prompt_executor")
                )
            )
        return updated_node
```

**Step 2: Type renames**

```python
    def leave_Name(self, original_node, updated_node):
        renames = {
            "ClaudeExecutor": "PromptExecutor",
            "FakeClaudeExecutor": "FakePromptExecutor",
            "ClaudeEvent": "ExecutorEvent",
            "is_claude_available": "is_available",
        }
        if updated_node.value in renames:
            return updated_node.with_changes(value=renames[updated_node.value])
        return updated_node
```

**Step 3: Context field updates**

```python
    def leave_Attribute(self, original_node, updated_node):
        if m.matches(updated_node, m.Attribute(
            value=m.Name("ctx"),
            attr=m.Name("claude_executor")
        )):
            return updated_node.with_changes(attr=cst.Name("prompt_executor"))
        return updated_node
```

#### Applying the Consolidation

```bash
# Dry run (preview changes)
python -m libcst.tool codemod --no-format prompt_executor_consolidation.py src/ tests/

# Apply changes
python -m libcst.tool codemod prompt_executor_consolidation.py src/ tests/

# Verify with tests
make test-unit
```

### Partial Path Matching Is the Most Common Bug

A matcher for `erk_shared.gateway` will also match `erk_shared.gateway.git`. The fix is to match the complete module path, not just a prefix. When writing matchers for deeply nested import paths, the nested `m.Attribute()` structure is verbose but necessary — each level must be explicit.

When in doubt, add a guard that extracts the full module path as a string:

```python
if m.matches(node, m.ImportFrom(module=...)):
    module_str = cst.Module([]).code_for_node(node.module)
    if module_str == "erk_shared.gateway.command_executor":
        # Transform only this exact path
        ...
```

### The `with_changes()` Gotcha

Always use `with_changes()` on the `updated_node` rather than reconstructing a full node. Reconstructing from scratch loses comments, whitespace, and trailing commas that LibCST tracks in its concrete syntax tree:

```python
# GOOD — preserves comments and formatting
return updated_node.with_changes(module=new_module)

# BAD — loses comments, whitespace, trailing commas
return cst.ImportFrom(module=new_module, names=updated_node.names)
```

This is the most common cause of "formatting changed unexpectedly" after a LibCST pass.

### Relative Imports Should Be Skipped

Transformers that update absolute import paths must not touch relative imports (`.abc`, `.types`). Relative imports are internal to the moved package and remain correct after the move. Guard against this early:

```python
# Skip relative imports — they're internal to the package
if updated_node.relative:
    return updated_node
```

### Type Name Renames Need Scope Guards

A naive `leave_Name` that renames "Claude" to "Prompt" will also rename user-facing strings containing "Claude". Scope the rename to exact class/type names, and use a whitelist dictionary rather than substring matching.

## Testing Transformations

Before applying to the full codebase:

1. **Test on a single file** — verify transformation works correctly
2. **Check diff** — ensure only intended changes appear
3. **Run tests** — catch broken imports
4. **Run linter** — fix formatting issues

```bash
# Test on one file (preview diff)
python scripts/refactor_imports.py < packages/foo/bar.py | diff -u packages/foo/bar.py -

# Apply to one file and verify
python scripts/refactor_imports.py < packages/foo/bar.py > packages/foo/bar.py.tmp
mv packages/foo/bar.py.tmp packages/foo/bar.py
pytest tests/unit/test_bar.py
```

## Sources

- [LibCST documentation](https://libcst.readthedocs.io/) — full API reference for matchers, visitors, and transformers

## Related Documentation

- [Gateway Consolidation Checklist](../planning/gateway-consolidation-checklist.md) — the full refactoring workflow that LibCST plugs into
- [Gateway ABC Implementation Checklist](../architecture/gateway-abc-implementation.md) — the 5-place pattern that must be updated during consolidation
- [Re-Export Pattern](../architecture/re-export-pattern.md) — temporary re-exports during migration, cleaned up after LibCST pass
