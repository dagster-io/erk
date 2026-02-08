---
title: Language Scope Auditing
read_when:
  - writing documentation that includes non-Python code examples
  - documenting erkdesk or desktop-dash patterns in docs/learned/
  - reviewing learned-docs for verbatim code across languages
last_audited: "2026-02-08"
audit_result: clean
tripwires:
  - action: "including TypeScript/Bash code blocks from erkdesk"
    warning: "Including TypeScript/Bash code blocks from erkdesk/ without checking the One Code Rule"
  - action: "auditing non-Python code in learned docs"
    warning: "Assuming the verbatim copy prohibition only applies to Python"
  - action: "documenting erkdesk patterns"
    warning: "Rationalizing erkdesk source as \"third-party API pattern\" because it uses React/Electron"
---

# Language Scope Auditing

## Why This Matters

The One Code Rule is language-agnostic: no reproduced source code regardless of language. However, agents have a strong Python bias when self-policing — they instinctively flag `class Foo:` or `def bar(` as potential violations but let TypeScript interfaces and React component definitions pass unchallenged.

This is a practical problem because `erkdesk/` contains substantial TypeScript source, and `docs/learned/desktop-dash/` documents patterns from that code. The same staleness dynamics apply: a copied React component or Electron preload bridge goes stale just as silently as a copied Python class.

## The Blind Spot: Non-Python Code Blocks

<!-- Source: .github/reviews/audit-pr-docs.md, Step 2-4 -->

The audit tooling (`.github/reviews/audit-pr-docs.md` review + `/local:audit-doc`) is methodologically language-agnostic — it extracts code references and matches against source files regardless of language. But effectiveness varies in practice:

| Language   | Source Location | Audit Effectiveness | Why                                                           |
| ---------- | --------------- | ------------------- | ------------------------------------------------------------- |
| Python     | `src/erk/`      | High                | Primary codebase language; agents and tooling well-calibrated |
| TypeScript | `erkdesk/`      | Lower               | Agents less likely to flag; fewer TypeScript auditing habits  |
| Bash       | Scripts, hooks  | Lowest              | Often inline/ad-hoc; harder to match against specific sources |

The four exceptions from the One Code Rule still apply across all languages: data formats, third-party API patterns (React hooks, Electron IPC), anti-patterns marked WRONG, and I/O examples.

## Anti-Pattern: Language-Based Exception Creep

Agents sometimes rationalize keeping TypeScript code blocks by treating them as "third-party API patterns" when they're actually verbatim copies of erk source that happens to use React or Electron APIs.

**The test**: Does the code block copy from a file in `erkdesk/`? If yes, it's erk source — not a third-party pattern — regardless of what frameworks it uses. A React component defined in `erkdesk/src/renderer/components/` is erk source, not a React teaching example.

## Related Documentation

- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — Rationale for the prohibition
- [source-pointers.md](source-pointers.md) — Replacement format for verbatim code
