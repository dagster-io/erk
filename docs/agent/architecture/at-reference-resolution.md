---
title: "@ Reference Resolution"
read_when:
  - "Modifying @ reference validation"
  - "Debugging broken @ references in symlinked files"
  - "Understanding why validation passes but Claude Code fails"
---

# @ Reference Resolution

How @ references are resolved in Claude Code vs. the erk validation code.

## Claude Code Behavior

Claude Code resolves @ references from the **literal file path**, not following symlinks:

- File at `.claude/commands/foo.md` (symlink to `packages/.../foo.md`)
- Contains `@../../docs/bar.md`
- Claude Code resolves from `.claude/commands/` → looks for `docs/bar.md`
- Does NOT resolve from `packages/.../commands/`

## Validation Code Behavior

The `md check --check-links` validation in `link_validation.py` must match Claude Code's behavior:

1. Use the symlink's parent directory for relative path resolution
2. Do NOT follow the symlink to get the target's parent
3. After resolving the relative path, it's OK to follow symlinks on the TARGET file

## Key Distinction

- **Source file symlink**: Do NOT follow (use literal location)
- **Target file symlink**: OK to follow (a symlinked doc file is still valid)

## Related Files

- `packages/dot-agent-kit/src/dot_agent_kit/io/link_validation.py`
- `packages/dot-agent-kit/src/dot_agent_kit/io/at_reference.py`
