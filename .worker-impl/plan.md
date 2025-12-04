# Plan: Documentation Extraction from Session

## Objective

Extract documentation improvements identified from session analysis of symlink validation bug discovery and fix.

## Source Information

- **Source Plan Issues:** [#2161]
- **Extraction Session IDs:** ["910ffc71-5e9e-4982-a93d-76fd50e0b03e"]

## Documentation Items

### Item 1: Python pathlib Symlink Behavior

**Type:** Agent Doc
**Location:** `docs/agent/architecture/pathlib-symlinks.md`
**Action:** New doc
**Priority:** Medium

**Content:**

```markdown
# Python pathlib Symlink Behavior

Understanding how Python's `pathlib` handles symlinks is critical for writing correct validation and file operation code.

## Key Behaviors

### Path.exists() Follows Symlinks

`Path.exists()` returns `True` if the **target** of a symlink exists, not just if the symlink itself exists.

```python
symlink = Path(".claude/commands/foo.md")  # symlink -> packages/.../foo.md
symlink.exists()  # Returns True if packages/.../foo.md exists
```

### Path.resolve() Follows Symlinks

`Path.resolve()` returns the **canonical path** after following all symlinks.

```python
symlink = Path(".claude/commands/foo.md")
symlink.resolve()  # Returns /abs/path/to/packages/.../foo.md
```

### Path Arithmetic with Symlinks

When you do `symlink.parent / "../foo"`, Python doesn't follow the symlink during path construction. However, when you later call `.exists()` or `.resolve()`, the symlink IS followed.

```python
symlink = Path(".claude/commands/foo.md")  # -> packages/.../foo.md
relative = symlink.parent / "../../docs/bar.md"
# relative = .claude/commands/../../docs/bar.md (literal)
# But relative.exists() resolves through the symlink!
```

## Common Pitfall

When validating relative paths in symlinked files, `Path.exists()` may return `True` even when the path wouldn't work from the symlink's literal location.

**Fix:** Use `os.path.normpath()` to normalize paths without following symlinks, then check existence.

## Read When

- Writing file validation code
- Debugging unexpected path resolution behavior
- Working with symlinked configuration files
```

### Item 2: @ Reference Resolution Architecture

**Type:** Agent Doc
**Location:** `docs/agent/architecture/at-reference-resolution.md`
**Action:** New doc
**Priority:** High

**Content:**

```markdown
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

## Read When

- Modifying @ reference validation
- Debugging broken @ references in symlinked files
- Understanding why validation passes but Claude Code fails
```

### Item 3: Symlink Validation Pattern

**Type:** Agent Doc
**Location:** `docs/agent/architecture/symlink-validation-pattern.md`
**Action:** New doc
**Priority:** Medium

**Content:**

```markdown
# Symlink-Aware Validation Pattern

Pattern for validating paths when the source file may be a symlink.

## Problem

Python's `Path.exists()` follows symlinks transparently. When validating relative paths in symlinked files, this can cause false positives where validation passes but runtime fails.

## Solution Pattern

```python
import os
from pathlib import Path

def validate_relative_path(
    relative_path: str,
    source_file: Path,
    repo_root: Path,
) -> bool:
    """Validate relative path from source file's literal location.

    When source_file is a symlink, validates from the symlink's
    location, NOT the target's location.
    """
    # Get literal parent (don't follow symlink)
    parent = source_file.parent

    # Construct and normalize path WITHOUT following symlinks
    raw_path = parent / relative_path
    normalized = Path(os.path.normpath(str(raw_path)))

    # Now check existence (following symlinks on TARGET is OK)
    return normalized.exists()
```

## Key Points

1. `source_file.parent` gives the symlink's directory, not target's
2. Use `os.path.normpath()` to resolve `..` components without following symlinks
3. The final `.exists()` check CAN follow symlinks (for the target file)

## When to Apply

- Validating @ references in markdown files
- Validating import paths in configuration
- Any path validation where source files may be symlinks

## Related Issue

- #2161 - Fix Symlink @ Reference Validation Bug
```