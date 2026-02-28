---
title: Language Scope Auditing
read_when:
  - writing documentation that includes non-Python code examples
  - reviewing learned-docs for verbatim code across languages
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
tripwires:
  - action: "copying non-Python code verbatim"
    warning: "Assuming the verbatim copy prohibition only applies to Python"
---

# Language Scope Auditing

## Why This Matters

The One Code Rule is language-agnostic: no reproduced source code regardless of language. However, agents have a strong Python bias when self-policing — they instinctively flag `class Foo:` or `def bar(` as potential violations but let other languages pass unchallenged.

## The Blind Spot: Non-Python Code Blocks

<!-- Source: .erk/reviews/audit-pr-docs.md, Step 2-4 -->

The audit tooling (`.erk/reviews/audit-pr-docs.md` review + `/local:audit-doc`) is methodologically language-agnostic — it extracts code references and matches against source files regardless of language.

The four exceptions from the One Code Rule still apply across all languages: data formats, third-party API patterns, anti-patterns marked WRONG, and I/O examples.

## Related Documentation

- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — Rationale for the prohibition
- [source-pointers.md](source-pointers.md) — Replacement format for verbatim code
