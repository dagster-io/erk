---
title: Source Pointers
read_when:
  - writing or updating documentation with code references
  - deciding whether to include a code block in docs
  - addressing verbatim code violations from audit-pr-docs review
tripwires:
  - action: "copying source code into a docs/learned/ markdown file"
    warning: "Use a source pointer instead. See source-pointers.md for the two-part format (HTML comment + prose reference)."
  - action: "using line numbers in source pointers"
    warning: "Prefer name-based identifiers (ClassName.method) over line numbers. Names survive refactoring; line numbers go stale silently."
last_audited: "2026-02-08"
audit_result: edited
---

# Source Pointers

Source pointers are the canonical format for referencing code from `docs/learned/` files. They exist because verbatim code blocks silently go stale — a copied function signature looks authoritative even after the real signature changed three PRs ago. Source pointers replace this silent failure with a loud one: a stale file path or symbol name is immediately obvious when an agent tries to navigate to it.

For the deeper rationale behind this trade-off, see [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md).

## The Two-Part Format

Every source pointer has two parts that serve different audiences: an HTML comment for tooling and a prose reference for agents.

**Part 1 — HTML comment** (machine-readable, enables automated staleness detection):

```markdown
<!-- Source: path/to/file.py, ClassName.method_name -->
```

**Part 2 — Prose reference** (tells agents what to grep for):

```markdown
See `ClassName.method_name()` in `path/to/file.py`.
```

Both parts are required. The HTML comment is what `audit-pr-docs` scans for during PR review. The prose reference is what agents actually read when navigating to source. Omitting either part defeats half the system.

## Identifier Style Decision

| Style          | Format                      | Use when                                           | Staleness behavior                                                      |
| -------------- | --------------------------- | -------------------------------------------------- | ----------------------------------------------------------------------- |
| **Name-based** | `file.py, ClassName.method` | Python source with stable symbols                  | Low risk — names survive refactoring, grep still finds them             |
| **Line-range** | `file.py:20-69`             | Markdown, YAML, config files without named symbols | Medium risk — any edit shifts line numbers, but the mismatch is obvious |

**Default to name-based.** Line-range is the fallback for files that lack greppable symbol names (markdown sections, YAML blocks, config stanzas). Even a stale line-range is better than a stale code block — the line-range fails visibly when the range doesn't match the expected content.

## When to Use Source Pointers vs Code Blocks

Source pointers replace all code blocks _except_ the four cases where the One Code Rule grants an exception. The decision is mechanical:

| Content type                                              | Action               | Reasoning                                                                      |
| --------------------------------------------------------- | -------------------- | ------------------------------------------------------------------------------ |
| Erk source code (any length)                              | Replace with pointer | Will drift from reality; the source file is the authority                      |
| Data format examples (JSON, YAML, TOML)                   | Keep as code block   | Shows structural shape, not implementation logic                               |
| Third-party API patterns (Click, pytest, Rich)            | Keep as code block   | Teaching external API usage that isn't in erk's source                         |
| Anti-patterns marked WRONG                                | Keep as code block   | The wrongness is the point — these are intentionally incorrect                 |
| CLI invocation examples (with or without output)          | Keep as code block   | Usage examples document the command's interface, not implementation logic      |
| Command output format (JSON a command returns)            | Keep as code block   | Documents the output contract for callers, not implementation                  |
| Third-party reference tables (API endpoints, syntax refs) | Keep as code block   | Token cache of expensive-to-fetch external docs (include `## Sources` section) |

**CLI examples matching docstrings are not verbatim copies.** A bash invocation example like `erk exec foo --bar baz` naturally looks identical whether it appears in a docstring or in documentation. This is expected — both are documenting the same CLI interface. Do not flag these as VERBATIM.

**Partial excerpts are not an exception.** Copying "just the interesting lines" from a source file creates the same staleness problem as copying the whole function. If the code is erk source, use a pointer regardless of length.

## Pointer Target Selection

**Point to the most stable identifier available.** This is the single most important decision when writing a source pointer, because it determines how quickly the pointer goes stale.

Stability hierarchy (most stable → least stable):

1. **ABC definitions** — abstract interfaces change rarely and concrete implementations must conform to them
2. **Schema/config classes** — Pydantic models, frozen dataclasses define the shape of data
3. **Public method names** — refactoring usually preserves these even when internals change
4. **Line numbers** — any edit to the file shifts them

**Anti-pattern**: Pointing to a concrete gateway implementation that changes weekly. Point to the ABC method definition instead — it captures the contract, and any implementation must conform to it. This is why `simplification-patterns.md` lists ABCs as the top priority for pointer targets.

**Anti-pattern**: Pointing to a function's body when its class or module docstring captures the same concept. Prefer the highest-level stable symbol that communicates the insight.

## Automated Enforcement

<!-- Source: .erk/reviews/audit-pr-docs.md -->

The `audit-pr-docs` review automatically runs on every PR touching `docs/learned/`. It audits the full document (not just changed lines), classifies code blocks as VERBATIM or permitted, and posts inline comments with the exact source path and suggested pointer format. When you receive one of these comments, convert the code block to a source pointer using the two-part format above.

This enforcement connects to the broader audit system: `/local:audit-doc` performs deep single-document analysis, `/local:audit-scan` triages which docs need audit, and `audit-pr-docs` prevents new problems at PR time. See [audit-methodology.md](audit-methodology.md) for the full classification framework.

## Related Documentation

- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — The deeper case for why pointers beat embedded code
- [simplification-patterns.md](simplification-patterns.md) — Pattern 1 (Static → Dynamic) uses source pointers as its fix
- [audit-methodology.md](audit-methodology.md) — How audits classify VERBATIM blocks for replacement
