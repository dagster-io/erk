---
title: Refactoring Tripwires
read_when:
  - "working on refactoring code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from refactoring/*.md frontmatter -->

# Refactoring Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before interleaving file moves and import updates** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. Move ALL files first (git mv), THEN batch-update ALL imports. Interleaving creates intermediate broken states. See gateway-consolidation-checklist.md.

**CRITICAL: Before manually updating imports across 10+ files** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. Use LibCST via the libcst-refactor agent or a one-off script. Manual editing misses call sites and creates partial migration states.

**CRITICAL: Before writing LibCST transformation logic from scratch** → Read [LibCST Systematic Import Refactoring](libcst-systematic-imports.md) first. The libcst-refactor agent (.claude/agents/libcst-refactor.md) contains battle-tested patterns, gotchas, and a script template. Load it first.
