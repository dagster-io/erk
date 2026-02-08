---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - writing markdown in docs/learned/ and wondering how Prettier will reformat it
  - choosing between tables, lists, and prose in documentation
  - using prettier-ignore directives in documentation
title: Markdown Authoring and Prettier Interactions
tripwires:
  - action: manually wrapping lines or aligning tables in markdown
    warning:
      Never manually format markdown. Prettier rewrites all formatting on save.
      Write naturally, then run `make prettier` via devrun.
  - action: adding prettier-ignore to docs/learned/
    warning:
      prettier-ignore is almost never needed in docs. If Prettier is mangling
      your content, the structure may need rethinking rather than suppression.
---

# Markdown Authoring and Prettier Interactions

## Why This Doc Exists

Prettier enforces deterministic formatting on all committed markdown. This is well-documented in CI docs. What's _not_ obvious is how Prettier's behavior should influence the way agents **author** documentation in `docs/learned/`. Certain markdown patterns interact poorly with Prettier's reformatter, and understanding these interactions prevents wasted edit cycles.

For the operational workflow (how to run Prettier, CI integration, devrun delegation), see [Markdown Formatting in CI Workflows](../ci/markdown-formatting.md).

## Write for the Reformatter, Not Against It

Prettier will rewrite every line of prose to fit within 80 characters. This has consequences for how agents should write:

**Don't manually wrap lines.** Write prose as continuous text. Prettier will insert its own line breaks at semantic boundaries. Manual wrapping creates awkward mid-sentence breaks after Prettier re-wraps around them.

**Don't align table columns.** Prettier normalizes all table alignment. Any manual padding is wasted effort — and creates noisy diffs when Prettier reformats.

**Don't count characters.** Prettier's wrapping algorithm considers inline code spans, links, and emphasis markers when calculating line length. Manual character counting cannot replicate this logic.

## Formatting Patterns That Survive Prettier

| Pattern          | Prettier Behavior                | Authoring Guidance                             |
| ---------------- | -------------------------------- | ---------------------------------------------- |
| Prose paragraphs | Rewrapped at ~80 chars           | Write as single long lines                     |
| Bullet lists     | Normalized indentation/spacing   | Use 2-space indent for nesting                 |
| Tables           | Column alignment enforced        | Don't bother aligning — Prettier will          |
| Code blocks      | Content preserved verbatim       | Safe zone — Prettier won't touch internals     |
| YAML frontmatter | Left completely untouched        | Also a safe zone                               |
| URLs in prose    | Never wrapped mid-URL            | Long URLs won't cause line-length issues       |
| Headings         | Blank line enforced before/after | Always include blank lines to avoid diff noise |

## When Prettier Fights Your Intent

Occasionally Prettier's reformatting changes the semantic meaning of documentation. The most common case is **tables with precise alignment** that convey structure visually. In these rare cases, `<!-- prettier-ignore -->` before the block suppresses reformatting.

**The bar for prettier-ignore is high.** In practice, it's almost never needed in `docs/learned/`. If Prettier is mangling your content, the first question should be "is there a better way to structure this?" — not "how do I suppress Prettier?"

Legitimate uses: ASCII diagrams, carefully formatted comparison tables where column alignment carries meaning, markdown that embeds non-standard syntax.

## Anti-Patterns

### Manual Line Wrapping

Counting characters and inserting line breaks. Prettier will re-wrap anyway, often creating worse breaks than if the prose had been written as a single continuous line.

### Edit-Tool Formatting Fixes

After a prettier-check CI failure, using Edit to adjust line breaks or spacing. This is a losing game — run `make prettier` via devrun instead. See the devrun delegation pattern in [Markdown Formatting in CI Workflows](../ci/markdown-formatting.md).

### Over-Using prettier-ignore

Suppressing Prettier because the output "looks wrong." Prettier's formatting is the project standard. If it reformats something unexpectedly, either the markdown structure needs adjustment or the content belongs in a code block (which Prettier won't touch).

## Configuration Context

Erk uses Prettier's defaults (no `.prettierrc`) with one configuration choice: `--ignore-path .gitignore` instead of `.prettierignore`. This means gitignored files are automatically excluded from formatting. The `.prettierignore` file that exists in the repo is not used by the Makefile targets.

<!-- Source: Makefile, prettier and prettier-check targets -->

See the `prettier` and `prettier-check` targets in the Makefile for the exact invocation. For the full story on why `.prettierignore` is bypassed, see [Makefile Prettier Ignore Path](../ci/makefile-prettier-ignore-path.md).

## Related Documentation

- [Markdown Formatting in CI Workflows](../ci/markdown-formatting.md) — operational workflow, devrun delegation, CI integration
- [Prettier Formatting for Claude Commands](../ci/claude-commands-prettier.md) — `.claude/commands/` specific patterns
- [Stale Code Blocks Are Silent Bugs](stale-code-blocks-are-silent-bugs.md) — why source pointers beat code blocks (Prettier-safe by design)
