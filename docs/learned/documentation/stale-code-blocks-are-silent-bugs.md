---
title: Stale Code Blocks Are Silent Bugs
read_when:
  - documenting implementation patterns with code examples
  - deciding whether to include verbatim code in docs
  - understanding documentation maintenance trade-offs
---

# Stale Code Blocks Are Silent Bugs

When documenting implementation patterns in `docs/learned/`, verbatim code blocks are a silent source of technical debt. They drift from the source code silently, misleading readers with outdated patterns that appear authoritative.

## The Problem: Silent Drift

Verbatim code blocks copied from source files go stale when the implementation changes:

- **No compile-time feedback** when the source changes
- **No runtime errors** when the docs diverge
- **No obvious symptoms** to readers that the code is outdated
- **False confidence** from seeing concrete code examples

Stale code is worse than no code—it teaches the wrong patterns while appearing canonical.

## Why Stale Line Numbers Are Better

Source pointers (file path with line range) intentionally go stale when the source changes. This is a feature, not a bug:

| Failure Mode      | Detection                                 | Fix Effort                                    | Risk Level                            |
| ----------------- | ----------------------------------------- | --------------------------------------------- | ------------------------------------- |
| Stale code block  | None (silent)                             | High (requires comparing with current source) | **Critical** (teaches wrong patterns) |
| Stale line number | Obvious (line range doesn't match method) | Low (jump to file, update range)              | **Low** (reader knows to verify)      |

Stale line numbers fail loudly. Stale code blocks fail silently.

## The Solution: Source Pointer Pattern

Replace verbatim code blocks longer than 5 lines with a two-part reference:

### Part 1: HTML Comment with Line Range

```markdown
<!-- Source: path/to/file.py:START-END -->
```

### Part 2: Prose Reference with Context

```markdown
See `ClassName.method_name()` in `path/to/file.py:START-END`.
```

**Why this works:**

1. **Readers get the exact location** to find current implementation
2. **Stale line numbers are obvious** when they don't match the method
3. **Prose provides context** about what's important to notice
4. **Tooling can validate** that file paths and line ranges exist

See [source-pointers.md](source-pointers.md) for complete format specification.

## Detection: PR-Time Review Automation

The `.github/reviews/learned-docs.md` review runs on every PR touching `docs/learned/`:

- **Scans `+` diff lines** for code blocks longer than 5 lines
- **Detects verbatim copies** by matching against source files
- **Posts inline comments** with exact source path and line numbers
- **Suggests source pointer format** as replacement

When you receive a learned-docs review comment, it means you've included verbatim source that should be converted to a source pointer.

<!-- Source: .github/reviews/learned-docs.md:20-69 -->

See the automated detection logic in `.github/reviews/learned-docs.md:20-69` (Step 2-4: extract code blocks, check for matches, classify as verbatim).

## When Short Code Blocks Are Okay

Keep verbatim code blocks (≤5 lines) when:

- **Showing external library patterns** (not erk source)
- **Illustrating a general concept** with made-up names
- **Providing CLI command examples** with output
- **Demonstrating config file syntax** (YAML, TOML, JSON)

The 5-line threshold balances illustration value against staleness risk.

## Maintenance Trade-offs

**Accepting stale pointers:**

- Line numbers change when source code evolves
- Readers must verify the pointer still matches the method
- Tooling can validate file paths exist (future enhancement)

**Rejecting stale code:**

- Outdated patterns teach wrong implementation habits
- No automated way to detect divergence
- Misleads readers with false confidence

This is an intentional trade-off: fail loudly (stale pointers) instead of silently (stale code).

## Related Documentation

- [source-pointers.md](source-pointers.md) - Complete source pointer format specification
- `.github/reviews/learned-docs.md` - Automated PR-time detection of verbatim copies
