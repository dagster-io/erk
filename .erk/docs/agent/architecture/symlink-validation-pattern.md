---
title: Symlink-Aware Validation Pattern
read_when:
  - Validating @ references in markdown files
  - Validating import paths in configuration
  - Any path validation where source files may be symlinks
---

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

## Related Issue

- #2161 - Fix Symlink @ Reference Validation Bug
