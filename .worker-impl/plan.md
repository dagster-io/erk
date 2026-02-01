# Plan: Prevent Verbatim Code Blocks in Learn Pipeline

## Problem

The learn pipeline generates documentation with verbatim code blocks (especially TypeScript/JS), which then get flagged in PR review as needing replacement with source pointers. This creates busywork. The fix should be upstream — prevent the docs from being generated with verbatim code in the first place.

## Root Causes

1. **SKILL.md is Python-only**: Rules say "NEVER embed Python functions" but TypeScript, JavaScript, and other language code blocks pass through unchecked
2. **Learn pipeline doesn't know about source pointers**: The plan-synthesizer generates draft content with verbatim code because it has no instruction to use source pointers. `docs/learned/documentation/source-pointers.md` exists but isn't referenced by any pipeline agent
3. **Line number contradiction**: SKILL.md says "NEVER include line numbers" but source-pointers.md's two-part pattern requires them

## Changes (3 files)

### 1. Broaden SKILL.md to all languages

**File:** `.claude/skills/learned-docs/SKILL.md`

**Edit 1a — Line 160**: Change opening rule from Python-specific to language-agnostic:
- Before: `NEVER embed Python functions that process erk data...`
- After: `NEVER embed functions or class implementations from ANY language that process erk data or encode business logic. This applies to Python, TypeScript, JavaScript, and all other languages.`

**Edit 1b — Line 164**: Broaden from "Embedded Python code" to "Embedded source code"

**Edit 1c — Lines 186-194**: Broaden "What to REMOVE" from "Remove ALL Python `def` functions" to cover all languages (Python `def`, TypeScript/JS `function`, arrow functions, class methods). Add two new bullets:
- Mock/stub implementations of browser/runtime APIs (ResizeObserver, IntersectionObserver)
- TypeScript type definitions that duplicate source types

**Edit 1d — Line 219**: Broaden external library examples to include React hooks

**Edit 1e — Lines 225-236**: Broaden Decision Test from Python-only to all languages. Add item 8: "Is it >5 lines copied from an erk source file? → REMOVE, use source pointer"

**Edit 1f — Lines 270-275**: Replace "Source Pointer Rules" section. Remove "NEVER include line numbers" (contradicts source-pointers.md). Instead, defer to the canonical guide:
```
Follow the canonical guide in `docs/learned/documentation/source-pointers.md`. Key rules:
- Use the two-part pattern: HTML comment with line range + prose reference
- Source pointers use line numbers (easier to fix than stale code blocks)
- Prefer CLI commands over source pointers when available
```

### 2. Add source pointer guidance to plan-synthesizer

**File:** `.claude/agents/learn/plan-synthesizer.md`

**Edit 2a — Step 4 (after line 69)**: Add new sub-item to the documentation item generation step:
```
4. **Use source pointers, not verbatim code**: Draft content MUST NOT include verbatim code blocks copied from source files. Instead:
   - Describe what the code does in prose
   - Point to the source file: `See ClassName.method() in path/to/file.py:LINE-LINE`
   - Short illustrative snippets (≤5 lines) showing a pattern are acceptable
   - Follow `docs/learned/documentation/source-pointers.md` for format
```

**Edit 2b — Key Principles (after line 193)**: Add principle 6:
```
6. **Source pointers over verbatim code**: Draft content starters MUST use source file references instead of copying code blocks. Code in documentation goes stale silently. See `docs/learned/documentation/source-pointers.md`.
```

### 3. Add source locations to code-diff-analyzer inventory

**File:** `.claude/agents/learn/code-diff-analyzer.md`

**Edit 3a — Line 42**: Add bullet to inventory list: "Source locations for documentation pointers: for each item, note exact file path and line range for downstream source pointers"

**Edit 3b — Lines 63-66**: Add "Line Range" column to New Functions/Classes table

**Edit 3c — Lines 91-92**: Add source pointer info to recommended items format: `(source: path/to/file.py:LINE-LINE)`

**Edit 3d — After line 95**: Add "Source Pointer Awareness" section explaining that every inventory item MUST include source file path and line range, referencing `docs/learned/documentation/source-pointers.md`

## Defense in Depth

The pipeline flow with these changes:

1. **code-diff-analyzer** → inventory now includes source file locations (Change 3)
2. **documentation-gap-identifier** → passes through inventory data (no change needed)
3. **plan-synthesizer** → draft content uses source pointers instead of verbatim code (Change 2)
4. **Implementing agents** → `learned-docs` skill catches any remaining violations (Change 1)

## Verification

- Read the three modified files and confirm the guidance is clear and consistent
- Check that source-pointers.md is referenced from both SKILL.md and plan-synthesizer.md
- Confirm the line number contradiction is resolved (SKILL.md no longer says "NEVER include line numbers")