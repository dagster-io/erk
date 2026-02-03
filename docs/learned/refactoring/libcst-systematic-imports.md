---
title: LibCST Systematic Import Refactoring
last_audited: "2026-02-03 03:56 PT"
audit_result: edited
read_when:
  - "refactoring imports across many files"
  - "renaming modules or packages"
  - "consolidating gateway locations"
last_audited: "2026-02-03"
audit_result: edited
---

# LibCST Systematic Import Refactoring

Guide for using LibCST to systematically refactor imports across the codebase.

## Overview

LibCST is a Python library for parsing and transforming Python source code while preserving formatting and comments. It's ideal for mechanical refactoring tasks like updating imports.

**When to use:** Renaming modules, moving packages, or updating import paths across 10+ files.

**When not to use:** One-off changes to 1-2 files (use manual editing).

## Installation

LibCST is included in erk's dev dependencies:

```bash
uv sync --dev
```

## Basic Pattern

LibCST transformations follow this pattern:

1. **Define a visitor class** that identifies nodes to transform
2. **Implement transformation logic** in visitor methods
3. **Apply to files** using libcst's command-line tool or Python API

## Example: Gateway Path Consolidation

Problem: Moving `erk_shared.tui.commands.executor` to `erk_shared.gateway.command_executor`.

### Step 1: Write the Transformer

Create `scripts/refactor_command_executor_imports.py`:

```python
"""Refactor CommandExecutor imports to new gateway path."""

import libcst as cst
from libcst import matchers as m


class CommandExecutorImportTransformer(cst.CSTTransformer):
    """Transform CommandExecutor imports to new gateway location."""

    def leave_ImportFrom(
        self, original_node: cst.ImportFrom, updated_node: cst.ImportFrom
    ) -> cst.ImportFrom:
        """Transform import statements."""
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

        # Match: from erk_shared.tui.commands.real_executor import ...
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
                    attr=m.Name("real_executor"),
                )
            ),
        ):
            # Replace with: from erk_shared.gateway.command_executor.real import ...
            return updated_node.with_changes(
                module=cst.Attribute(
                    value=cst.Attribute(
                        value=cst.Attribute(
                            value=cst.Name("erk_shared"),
                            attr=cst.Name("gateway"),
                        ),
                        attr=cst.Name("command_executor"),
                    ),
                    attr=cst.Name("real"),
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
    transformed = module.visit(CommandExecutorImportTransformer())

    # Write output
    print(transformed.code, end="")
```

### Step 2: Apply to Files

```bash
# Find files with old imports
files=$(grep -rl "from erk_shared.tui.commands.executor" packages/ src/)

# Apply transformation
for file in $files; do
    python scripts/refactor_command_executor_imports.py < "$file" > "$file.tmp"
    mv "$file.tmp" "$file"
done
```

### Step 3: Fix Import Sorting

```bash
ruff check --fix packages/ src/
```

## Matchers Pattern Library

LibCST uses matchers to identify AST nodes. Common patterns:

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

### Function Call

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

## Advanced: Using libcst-agent

For complex transformations across many files, use the `libcst-refactor` agent via the Task tool:

```python
# In conversation with Claude Code
# User: "Update all imports of CommandExecutor to use the new gateway path"
# Claude: Uses Task tool with subagent_type='libcst-refactor'
```

The agent:

- Scans the codebase for matching patterns
- Generates transformation code
- Applies changes with verification
- Reports results

## Testing Transformations

Before applying to the codebase:

1. **Test on a single file** - verify transformation works
2. **Check diff** - ensure only intended changes
3. **Run tests** - catch broken imports
4. **Run linter** - fix formatting issues

```bash
# Test on one file
python scripts/refactor_imports.py < packages/foo/bar.py | diff -u packages/foo/bar.py -

# Apply and verify
python scripts/refactor_imports.py < packages/foo/bar.py > packages/foo/bar.py.tmp
mv packages/foo/bar.py.tmp packages/foo/bar.py
pytest tests/unit/test_bar.py
```

## Use Case: ABC Consolidation

LibCST is particularly valuable for ABC consolidation refactorings where you're merging two abstractions into one. The PromptExecutor consolidation (PR #6587) is a canonical example.

### Problem Statement

When consolidating `ClaudeExecutor` into `PromptExecutor`, you need to:

1. **Rename imports** - Update all `from ...claude_executor import ...` to `from ...prompt_executor import ...`
2. **Rename types** - Change `ClaudeExecutor` → `PromptExecutor`, `ClaudeEvent` → `ExecutorEvent`, etc.
3. **Update test constructors** - Rename `FakeClaudeExecutor(...)` → `FakePromptExecutor(...)`
4. **Update context fields** - Change `ctx.claude_executor` → `ctx.prompt_executor`

Across **40+ files** manually is error-prone. LibCST automates this.

### Transformation Strategy

**Step 1: Import path updates**

```python
class PromptExecutorImportTransformer(cst.CSTTransformer):
    def leave_ImportFrom(self, original_node, updated_node):
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
    # Rename class/type references
    renames = {
        "ClaudeExecutor": "PromptExecutor",
        "FakeClaudeExecutor": "FakePromptExecutor",
        "ClaudeEvent": "ExecutorEvent",
        "is_claude_available": "is_available"
    }
    if updated_node.value in renames:
        return updated_node.with_changes(value=renames[updated_node.value])
    return updated_node
```

**Step 3: Context field updates**

```python
def leave_Attribute(self, original_node, updated_node):
    # Match: ctx.claude_executor
    # Replace with: ctx.prompt_executor
    if m.matches(updated_node, m.Attribute(
        value=m.Name("ctx"),
        attr=m.Name("claude_executor")
    )):
        return updated_node.with_changes(attr=cst.Name("prompt_executor"))
    return updated_node
```

### Application

Run the transformer across the codebase:

```bash
# Dry run (preview changes)
python -m libcst.tool codemod --no-format prompt_executor_consolidation.py src/ tests/

# Apply changes
python -m libcst.tool codemod prompt_executor_consolidation.py src/ tests/

# Verify with tests
make test-unit
```

### Results from PR #6587

- **40+ files updated** - All imports, types, and references renamed
- **Zero manual edits** - Entirely automated with LibCST
- **Tests passed immediately** - Transformation was mechanically correct
- **2-hour refactor** - Would have taken days manually

### Lessons Learned

**Do:**

- Test transformer on 2-3 representative files first
- Use `with_changes()` to preserve formatting and comments
- Verify with `ruff check` and `make test-unit` after transformation

**Don't:**

- Rename types that have nothing to do with the consolidation (e.g., avoid renaming user-facing "Claude" strings)
- Transform relative imports (`.abc`, `.types`) inside moved packages
- Apply to the entire codebase without testing on a subset first

## Common Pitfalls

### Matching Partial Paths

**Problem:** Matcher matches more than intended.

**Example:** Matching `erk_shared.gateway` also matches `erk_shared.gateway.git`.

**Fix:** Use complete path matchers or add guards:

```python
if m.matches(node, m.ImportFrom(module=...)):
    # Verify exact module path
    module_str = cst.Module([]).code_for_node(node.module)
    if module_str == "erk_shared.gateway.command_executor":
        # Transform
        ...
```

### Preserving Comments

**Problem:** Comments get dropped during transformation.

**Fix:** LibCST preserves comments automatically - don't reconstruct entire nodes, use `with_changes()`:

```python
# GOOD - preserves comments
return updated_node.with_changes(module=new_module)

# BAD - loses comments
return cst.ImportFrom(module=new_module, names=updated_node.names)
```

### Breaking Relative Imports

**Problem:** Transformation breaks relative imports within moved package.

**Fix:** Keep relative imports relative:

```python
# If transforming: from .abc import Foo
# Leave it unchanged - relative imports are internal
if updated_node.relative:
    return updated_node
```

## Related Topics

- [Gateway Consolidation Checklist](../planning/gateway-consolidation-checklist.md) - Full consolidation process
- [libcst-refactor Agent](../../.claude/agents/libcst-refactor.md) - Automated refactoring
- [Gateway ABC Implementation](../architecture/gateway-abc-implementation.md) - Gateway structure
