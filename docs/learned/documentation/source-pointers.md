---
title: Source Pointers
read_when:
  - writing or updating documentation with code examples
  - deciding whether to include a code block in docs
  - addressing verbatim code violations in PRs
last_audited: "2026-02-05"
audit_result: clean
---

# Source Pointers

When documenting implementation patterns in `docs/learned/`, prefer source pointers over verbatim code copies. Code blocks longer than 5 lines that duplicate source will go stale when the implementation changes.

## When to Use Source Pointers

Use source pointers for code blocks that:

1. **Copy implementation details** from `src/erk/` or `packages/`
2. **Are longer than 5 lines** of actual code (not counting blank lines/comments)
3. **Will go stale** if the source changes

Short illustrative snippets (≤5 lines) are fine to include verbatim.

## Format: Two-Part Pattern

### Part 1: HTML Comment with Source File

Add an HTML comment before the prose reference:

```markdown
<!-- Source: path/to/file.py, ClassName.method_name -->
```

**Examples:**

```markdown
<!-- Source: packages/erk-shared/src/erk_shared/gateway/git/fake.py, FakeGit.add -->
<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, cast() pattern -->
```

### Part 2: Prose Reference with Method Name

Reference the specific class or method in prose:

```markdown
See `ClassName.method_name()` in `path/to/file.py`.
```

**Examples:**

```markdown
See `FakeGit.add()` in `packages/erk-shared/src/erk_shared/gateway/git/fake.py`.

See the `cast()` pattern in `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`.
```

Agents should grep for the class/function name to find the exact location in the file.

## Category System: What to Keep vs Remove

### Category A: Remove (Verbatim Copies)

**Always replace with source pointers:**

- Full method/function bodies (10+ lines)
- Constructor implementations with field initialization
- Complete class definitions with all methods
- Any substantial block (>5 lines) copied from real source files

**Why**: These will go stale. When the source changes, the docs become misleading.

### Category B: Keep (Illustrative Examples)

**Keep these as-is:**

- Short snippets (≤5 lines) showing key insights
- External library patterns (not erk source code)
- Config file examples (YAML, TOML, JSON)
- CLI command examples with output
- Made-up examples with fake names (`MyWidget`, `ExampleGateway`)

**Why**: These are teaching aids, not documentation of specific implementation.

### Category C: Transform (Partial Copies)

**Rewrite as source pointers plus context:**

- Partial method implementations showing only key lines
- Code blocks that excerpt the "interesting part" of a longer source
- Examples that combine multiple sources

**Why**: Even partial copies can become misleading. Better to point to the source and highlight what's important in prose.

## Decision Checklist

Before adding a code block to `docs/learned/`:

1. **Is it longer than 5 lines?** → Yes = Consider a pointer
2. **Does it copy from erk source?** → Yes = Strongly prefer pointer
3. **Will it go stale?** → Yes = Use pointer
4. **Is it showing a pattern, not implementation?** → Yes = Keep the code block

If you answered "Yes" to questions 1-3, use a source pointer.

## Maintenance Trade-offs

**Source pointers reference file paths and identifiers**, not line numbers. This avoids staleness:

- **File paths** rarely change; when they do, grep finds the new location
- **Class/function names** are stable identifiers that survive refactoring better than line numbers
- **Stale code blocks** are insidious (code still runs, just outdated patterns)
- No tooling can detect when copied code diverges from current implementation

## Automated Detection

The audit-pr-docs review (`.github/reviews/audit-pr-docs.md`) automatically detects verbatim source copies in PRs:

- Scans `docs/learned/**/*.md` files
- Matches code blocks against source files in `src/erk/` and `packages/`
- Posts inline comments identifying the source file and relevant identifiers
- Suggests source pointer format as replacement

When you receive a audit-pr-docs review comment, it means you should replace the code block with a source pointer.

## Examples in the Wild

See existing usage in:

- `docs/learned/testing/testing.md` - Multiple source pointers to gateway fakes
- `docs/learned/architecture/erk-architecture.md` - Pointers to planning and objective code
- `docs/learned/cli/exec-script-schema-patterns.md` - Pointers to TypedDict definitions

These files demonstrate the pattern after addressing verbatim code violations.
