<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->

# Refactoring Documentation

- **[bulk-rename-scope-verification.md](bulk-rename-scope-verification.md)** — running bulk rename tools (sed, libcst, ast-grep), verifying scope after a batch rename, distinguishing TUI renames from API renames
- **[frozen-dataclass-renames.md](frozen-dataclass-renames.md)** — renaming fields on frozen dataclasses, planning type-safe refactors, understanding why frozen dataclasses enable confident renames
- **[libcst-dependency-ordering.md](libcst-dependency-ordering.md)** — planning large-scale refactors, using libcst-refactor for bulk renames, avoiding intermediate broken states
- **[libcst-systematic-imports.md](libcst-systematic-imports.md)** — refactoring imports across many files, renaming modules or packages, deciding between manual edits and automated refactoring
- **[multi-pass-rename-verification.md](multi-pass-rename-verification.md)** — completing a libcst-refactor bulk rename, verifying all old references are gone after a rename, grepping for old field names after refactoring
- **[scope-discipline.md](scope-discipline.md)** — renaming fields that appear in multiple layers, distinguishing TUI changes from API changes, avoiding over-renaming during bulk refactors
- **[systematic-terminology-renames.md](systematic-terminology-renames.md)** — renaming a concept across the codebase (e.g., step→node), planning a multi-phase identifier rename, using LibCST for batch symbol renames
- **[type-safe-refactoring.md](type-safe-refactoring.md)** — planning large-scale refactors, understanding type safety benefits, working with frozen dataclasses
