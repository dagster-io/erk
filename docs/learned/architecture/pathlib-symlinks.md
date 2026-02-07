---
title: Python pathlib Symlink Behavior
read_when:
  - Writing file validation code
  - Debugging unexpected path resolution behavior
  - Working with symlinked configuration files
---

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
