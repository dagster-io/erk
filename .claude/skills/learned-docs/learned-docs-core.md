# Learned Documentation - Content Quality Standards

This is the single source of truth for what makes a good learned doc. All consumers (audit-doc, learn, PR reviews) reference these rules rather than embedding their own versions.

## The Cornerstone

Learned docs exist for **cross-cutting insight that can't live next to any single code artifact**.

Knowledge placement hierarchy (use the most specific option):

1. **Type artifact** — catalogs, fixed option sets, error codes → Literal types, Enums, constants in source
2. **Code comment** — insight about a single line or block
3. **Docstring** — insight about a single function or class
4. **Learned doc** — insight that spans multiple files, connects systems, or captures decisions

If knowledge can live in the code, it should. If it can be a type, it should be a type. Learned docs are the escalation path, not the default.

## Audience and Purpose

All documentation in `docs/learned/` is for **AI agents**, not human users. These docs are "token caches" — preserved reasoning and research so future agents don't have to recompute it.

**Document reality**, not aspiration. "This is non-ideal but here's the current state" is valuable documentation. Tech debt, workarounds, quirks — document them. Future agents need to know how things actually work.

**Bias toward capturing concepts** — when uncertain whether a cross-cutting insight is worth documenting, include it. But don't use this as license to document single-artifact knowledge that belongs in code comments or docstrings.

## Content Rules

### Explain Why, Not What

CORRECT: "We use LBYL instead of EAFP because exception-based control flow creates misleading error traces in agent sessions"

WRONG: "The `check_path()` function checks if a path exists before using it"

The "what" is already in the code. The "why" is what agents can't derive from reading source.

### Cross-Cutting Insight Is the Sweet Spot

The best learned docs connect multiple code locations into a coherent narrative:

- Decision tables ("when to use X vs Y")
- Patterns that span multiple files
- Historical context ("why not the obvious approach")
- Anti-patterns with explanations

### Anti-Patterns Earn Their Keep

Documenting what NOT to do — and why — is high-value. Future agents will be tempted by the obvious-but-wrong approach. Anti-pattern docs prevent them from re-learning the lesson.

## The One Code Rule

**Never reproduce source code.** Code blocks in docs are not under test and silently go stale, causing agents to copy outdated patterns.

### Four Exceptions

1. **Data formats** — JSON/YAML/TOML structure examples showing shape, not processing code
2. **Third-party API knowledge** — Click commands, pytest fixtures, Rich tables (teaching external APIs), API endpoint tables, DSL syntax references, expression catalogs, AND discovered/undocumented API behavior and quirks learned through usage. Include a `## Sources` section with URLs or usage context.
3. **Anti-patterns** — Code explicitly marked WRONG or DON'T DO THIS (the point is the wrongness)
4. **Input/output examples** — CLI commands with expected output, shell one-liners, command output format documentation (JSON/text showing what a command returns)

### The Decision Test

When in doubt: "Could an agent get this by reading the source?" If yes, use a source pointer instead.

For third-party APIs, two additional tests:

- "Is re-acquiring this expensive?" — fetching, parsing, and distilling external docs costs significant tokens. That's a reference cache worth preserving.
- "Is re-acquiring this impossible?" — undocumented behavior, quirks, and workarounds discovered through usage can't be found in any official docs. That's discovered knowledge and is the highest-value content.

For source pointer format, see `docs/learned/documentation/source-pointers.md`.

## What Belongs vs What Doesn't

### Belongs in Learned Docs

- Decision tables and trade-off analysis
- Anti-patterns with explanations
- Cross-cutting patterns spanning multiple files
- Historical context and architectural decisions
- Tripwires that prevent common mistakes
- External API quirks and workarounds
- Third-party reference material (stable API tables, DSL syntax, discovered quirks) with a `## Sources` section

### Doesn't Belong in Learned Docs

- Import paths (agents can grep)
- Function signatures (agents can read source)
- Docstring paraphrases
- Erk file listings with counts (go stale)
- Code that duplicates source (use source pointers)
- Single-artifact knowledge (use code comments or docstrings)
- Enumerable catalogs (error types, status values, config options) — encode as Literal types, Enums, or typed constants in source code with inline comments; reference with source pointers, not tables

## See Also

- `docs/learned/documentation/source-pointers.md` — canonical format for referencing source code
- `docs/learned/documentation/stale-code-blocks-are-silent-bugs.md` — the deeper case against embedded code
