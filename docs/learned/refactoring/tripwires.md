---
title: Refactoring Tripwires
read_when:
  - "working on refactoring code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from refactoring/*.md frontmatter -->

# Refactoring Tripwires

Rules triggered by matching actions in code.

**completing a libcst-refactor batch rename** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. After bulk rename, grep entire codebase for old symbol name. LibCST leave_Name visitor does NOT rename string literals used as dict keys. Subagent may miss files outside its scope.

**completing a terminology rename without grepping for string literals** → Read [Systematic Terminology Renames](systematic-terminology-renames.md) first. LibCST leave_Name visitor does NOT rename string literals used as dict keys. After LibCST batch rename, grep for old identifier as string key.

**interleaving file moves and import updates** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. Move ALL files first (git mv), THEN batch-update ALL imports. Interleaving creates intermediate broken states. See gateway-consolidation-checklist.md.

**manually updating imports across 10+ files** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. Use LibCST via the libcst-refactor agent or a one-off script. Manual editing misses call sites and creates partial migration states.

**renaming display strings without checking test assertions** → Read [Systematic Terminology Renames](systematic-terminology-renames.md) first. After display-string renames, search test assertions: `grep -r '"old_term"' tests/`. Not caught by linters or type checkers.

**running targeted edits after replace_all operations in the same file** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. During type migrations, complete all rename operations before attempting targeted edits. replace_all operations change strings that later edits expect to find.

**using replace_all on lines with trailing comments** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. Edit tool's replace_all removes surrounding whitespace, which can collapse lines and cause SyntaxError.

**using replace_all to rename foo to \_foo** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. Corrupts existing \_foo to \_\_foo. Grep for existing underscored forms before applying replace_all renames.

**writing LibCST transformation logic from scratch** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. The libcst-refactor agent (.claude/agents/libcst-refactor.md) contains battle-tested patterns, gotchas, and a script template. Load it first.
