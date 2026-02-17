---
title: "@ Reference Resolution"
last_audited: "2026-02-17 00:00 PT"
audit_result: clean
read_when:
  - "Modifying @ reference validation"
  - "Debugging broken @ references in symlinked files"
  - "Understanding why validation passes but Claude Code fails"
---

# @ Reference Resolution

How @ references are resolved in Claude Code and the rules for symlink handling.

## Claude Code Behavior

Claude Code resolves @ references from the **literal file path**, not following symlinks:

- File at `.claude/commands/foo.md` (symlink to `packages/.../foo.md`)
- Contains `@../../docs/bar.md`
- Claude Code resolves from `.claude/commands/` → looks for `docs/bar.md`
- Does NOT resolve from `packages/.../commands/`

## Key Distinction

- **Source file symlink**: Do NOT follow (use literal location)
- **Target file symlink**: OK to follow (a symlinked doc file is still valid)

When writing validation code for @ references, match this behavior:

1. Use the symlink's parent directory for relative path resolution
2. Do NOT follow the symlink to get the target's parent
3. After resolving the relative path, it's OK to follow symlinks on the TARGET file
