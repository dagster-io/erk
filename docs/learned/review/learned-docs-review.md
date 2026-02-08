---
title: Learned Docs Review
read_when:
  - working with learned documentation
  - understanding documentation quality checks
  - debugging verbatim code violations
tripwires:
  - action: "adding code blocks longer than 5 lines to docs/learned/ files"
    warning: "Verbatim source code will go stale. Use source pointers or short illustrative snippets instead. See learned-docs skill for guidance."
---

# Learned Docs Review

The Learned Docs Review is a GitHub review automation that detects and flags verbatim copies of source code in documentation files under `docs/learned/**/*.md`. When a PR adds code blocks longer than 5 lines that match real implementation sources, the review posts inline comments identifying the source file and suggesting replacements.

## What It Does

The review runs automatically on PRs that modify `docs/learned/**/*.md` files and:

1. **Scans code blocks** in changed documentation files
2. **Detects verbatim copies** by matching against source files in `src/erk/` and `packages/`
3. **Posts inline comments** with exact source file pointers and suggested fixes
4. **Maintains an activity log** tracking violations across PR iterations

## Why It Exists

**Problem**: Code rot in learned documentation.

When agents copy implementation code into docs (e.g., showing how a gateway works by pasting its actual source), that documentation silently becomes stale when the source changes. PR #2681 demonstrated this concretely: an agent copied incorrect scratch directory paths from documentation because the docs hadn't been updated when the implementation changed.

**Solution**: The audit-pr-docs review catches this at PR time rather than after merge.

## How It Works

### Detection Algorithm

The review uses heuristic-based detection rather than AST parsing:

1. **Import checks**: Looks for `from erk` or `import erk` patterns
2. **Name extraction**: Extracts class/function names via regex (`class Foo`, `def bar`)
3. **Source search**: Searches `src/erk/` and `packages/` for matching definitions
4. **Line matching**: Compares code block content against source files

A block is flagged as verbatim if:

- 3+ consecutive lines match a source file (ignoring whitespace/comments), OR
- The block contains a complete class/function definition that exists in source

### 5-Line Threshold

**Design decision**: Blocks of 5 lines or fewer are skipped even if they match source.

**Rationale**: Short snippets showing key insights are valuable documentation. The problem is large blocks (10+ lines) that represent substantial copied implementation and will drift from source over time.

### Classification

Code blocks are classified as:

- **Verbatim copy**: Real source code that will go stale → **FLAG IT**
- **Pattern/template**: Made-up names (MyGateway, ExampleWidget) → Skip
- **CLI/command example**: Bash commands or CLI output → Skip
- **Short snippet** (≤5 lines): Too small to matter → Skip

Only verbatim copies are flagged.

## Review Spec Details

**File**: `.github/reviews/audit-pr-docs.md`

**Frontmatter**: See `.github/reviews/audit-pr-docs.md:1-9` for the complete review specification.

**Key configuration**:

- **Model**: `claude-haiku-4-5` for fast mechanical extraction
- **Scope**: `docs/learned/**/*.md`
- **Tool constraints**: Read-only with GitHub CLI and erk exec access

## Inline Comment Format

When a violation is detected, the review posts:

```
**Audit PR Docs**: Verbatim source code copy detected.

Source: `<source_file_path>:<start_line>-<end_line>`

This code block copies ~N lines from the source file and will go stale if the source changes.

Suggested fix: Replace the code block with a source pointer:

> See `ClassName.method_name()` in `<relative_path>:<line>`.

If a short snippet is needed for context, keep it to ≤5 lines showing the key insight, with a pointer to the full source.
```

## Heuristic-Based Detection vs AST Parsing

The review uses **heuristics** rather than AST parsing. This design choice prioritizes:

- **Speed**: No import overhead, fast execution
- **Robustness**: Handles incomplete code blocks that would fail to parse
- **Tolerance**: Works with minor formatting differences

The detection flow:

1. Check for `from erk`/`import erk` patterns
2. Extract class/function names via regex
3. Perform line-matching against source files

This is sufficient for the review's purpose and avoids over-engineering.

## Integration Points

The audit-pr-docs review integrates with three existing erk systems:

1. **Convention-based review system** ([convention-based-reviews.md](../ci/convention-based-reviews.md)) - Uses standard frontmatter and discovery
2. **learned-docs skill** - Provides rationale for why verbatim code is problematic
3. **Learn workflow** - Creates documentation through plan-based review rather than direct writes

## Related Documentation

- `.github/reviews/audit-pr-docs.md` - The review specification
- `.claude/skills/learned-docs/SKILL.md` - Rationale for avoiding verbatim code
- `docs/learned/ci/convention-based-reviews.md` - How reviews fit in the broader system
- `docs/learned/review/inline-comment-deduplication.md` - Deduplication via markers
