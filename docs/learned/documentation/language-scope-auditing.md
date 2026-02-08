---
title: Language Scope Auditing
read_when:
  - writing documentation that includes code examples
  - reviewing learned-docs for verbatim code violations
  - understanding what code blocks are forbidden in docs/learned/
last_audited: "2026-02-07 18:40 PT"
audit_result: edited
---

# Language Scope Auditing

The verbatim copy prohibition in learned-docs applies to **all languages**, not just Python. Any code block longer than 5 lines that copies from source files in `src/erk/`, `packages/`, or `erkdesk/` should be replaced with a source pointer.

For the rationale behind this rule, see [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md). For the replacement format, see [source-pointers.md](source-pointers.md).

## Detection Patterns by Language

When reviewing `docs/learned/` for verbatim copies, flag code blocks (5+ lines) matching these patterns:

| Language   | Patterns to Flag                                                                |
| ---------- | ------------------------------------------------------------------------------- |
| Python     | `class Foo:`, `def bar(`, `from erk`, `@dataclass`, method/function bodies      |
| TypeScript | `interface Foo {`, `type Foo =`, `export function`, React component definitions |
| Bash       | Function definitions, multi-line script excerpts                                |
| Any        | Constructor implementations, fake/mock class bodies, test helper functions      |

**Fix for all**: Replace with a source pointer, or extract the key insight into 5 lines or fewer.

## Automation Gap

<!-- Source: .github/reviews/audit-pr-docs.md, Step 2-4 -->

The `.github/reviews/audit-pr-docs.md` review automates detection for **Python only** (class/function extraction, source matching against `src/erk/` and `packages/erk-shared/src/`).

**Not yet automated**: TypeScript, Bash, and other languages require manual review.

### Manual Audit Process

For non-Python code blocks:

1. **Extract language tag** from fenced code block
2. **Identify definitions** (interface, type, class, function)
3. **Search source** for matching definition names
4. **Compare content** (3+ consecutive matching lines = verbatim copy)
5. **Replace** with source pointer if verbatim copy detected

## Related Documentation

- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) - Why verbatim code is problematic
- [source-pointers.md](source-pointers.md) - How to replace verbatim code with pointers
- `.github/reviews/audit-pr-docs.md` - Automated detection for Python code
