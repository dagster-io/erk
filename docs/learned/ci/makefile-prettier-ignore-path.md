---
title: Makefile Prettier Ignore Path
read_when:
  - "creating .prettierignore file"
  - "adding patterns to exclude files from Prettier"
  - "debugging why .prettierignore has no effect"
tripwires:
  - score: 4
    action: "Creating or modifying .prettierignore"
    warning: "The Makefile uses `prettier --ignore-path .gitignore`, NOT `.prettierignore`. Adding rules to .prettierignore has no effect. Modify .gitignore to control what Prettier ignores."
    context: "This design keeps ignore patterns DRY - files ignored by git are also ignored by Prettier. Prettier's default .prettierignore support is bypassed by the --ignore-path flag."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Makefile Prettier Ignore Path

## Why .prettierignore Does Nothing

<!-- Source: Makefile, prettier and prettier-check targets -->

Erk's Makefile passes `--ignore-path .gitignore` to all Prettier invocations. This **overrides Prettier's default .prettierignore support entirely**. Creating or modifying `.prettierignore` has no effect because Prettier never reads it.

See the `prettier` and `prettier-check` targets in `Makefile`.

## The Design Constraint

This pattern enforces a deliberate constraint: **files in the repository must be formatted**. There is no escape hatch for "committed but unformatted" content.

The assumption: if a file should be committed, it should be formatted. If it shouldn't be formatted, it shouldn't be committed. This prevents the drift where checked-in files bypass CI formatting checks.

## Cross-Tool Consistency

The `--ignore-path .gitignore` pattern creates automatic synchronization:

- Build artifacts in `.gitignore` (like `dist/`, `.venv/`, `__pycache__/`) are automatically excluded from Prettier
- No duplication of ignore patterns across `.gitignore` and `.prettierignore`
- Agents working on formatting don't need to coordinate changes across multiple ignore files

When `.erk/scratch/` or `.impl/` are added to `.gitignore`, they're immediately excluded from Prettier without a second step.

## Working Around the Constraint

If you need to format a gitignored file (e.g., for local testing or generated documentation), invoke Prettier directly without the Makefile wrapper:

```bash
prettier --write path/to/gitignored-file.md
```

This bypasses the `--ignore-path .gitignore` flag and formats the file using Prettier's default behavior.

## Why Not Support Both?

Supporting both `.gitignore` and `.prettierignore` would allow "committed but unformatted" files to exist. This creates two problems:

1. **CI drift**: Formatting checks in CI might pass while local formatting fails (or vice versa) if the ignore files diverge
2. **Agent confusion**: Future agents would need to decide which file to modify when excluding content from formatting

The single-file design eliminates this decision point. Agents know: modify `.gitignore` to control formatting exclusions.
