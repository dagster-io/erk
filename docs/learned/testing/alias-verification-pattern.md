---
title: Import Alias Verification Pattern
read_when:
  - detecting import alias violations, implementing no-import-aliases rule checks, writing tests for import statement validation
---

# Import Alias Verification Pattern

Erk's dignified-python standard prohibits import aliases (`import X as Y` where `X != Y`), but allows re-export aliasing (`import X as X` for explicit re-export markers).

This document describes the pattern for detecting violations programmatically.

## The Rule

**Allowed:**

```python
import foo  # Standard import
from foo import Bar  # Named import
import foo as foo  # Re-export marker (explicit intention)
```

**Forbidden:**

```python
import foo as f  # Alias violation (X != Y)
import pandas as pd  # Common but forbidden
from typing import Dict as D  # Forbidden even in from-imports
```

## Detection Pattern

### Regex for Simple Import Aliases

To detect `import X as Y` where `X != Y`:

```python
import re

pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'

# Explanation:
# ^\s*              — Line start with optional whitespace
# import\s+         — "import" keyword with whitespace
# (\w+)             — Capture group 1: module name (X)
# \s+as\s+          — "as" keyword with whitespace
# (?!\1\b)          — Negative lookahead: reject if next word equals captured group
# \w+               — Alias name (Y)
# \s*$              — Optional whitespace, end of line

# Test cases
assert re.match(pattern, "import foo as f", re.MULTILINE)        # Match (violation)
assert re.match(pattern, "import pandas as pd", re.MULTILINE)    # Match (violation)
assert not re.match(pattern, "import foo as foo", re.MULTILINE)  # No match (re-export OK)
assert not re.match(pattern, "import foo", re.MULTILINE)         # No match (no alias)
```

### Full File Scan

To find all violations in a Python file:

```python
import re
from pathlib import Path

def find_import_aliases(file_path: Path) -> list[tuple[int, str]]:
    """Find all import alias violations in a file.

    Returns list of (line_number, line_content) tuples.
    """
    pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
    violations = []

    content = file_path.read_text()
    for line_num, line in enumerate(content.splitlines(), start=1):
        if re.match(pattern, line, re.MULTILINE):
            violations.append((line_num, line.strip()))

    return violations
```

### From-Import Aliases

The pattern above only handles `import X as Y`. To also catch `from X import Y as Z`:

```python
from_import_pattern = r'^\s*from\s+\w+\s+import\s+\w+\s+as\s+\w+\s*$'

# This is more permissive (doesn't check Y != Z) but catches the syntax
# Refine with capture groups if needed:
from_import_strict = r'^\s*from\s+\w+\s+import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
```

## Known Violations (13+ instances)

As of investigation, the codebase contains 13+ known import alias violations:

| File                                                            | Line    | Violation                                     |
| --------------------------------------------------------------- | ------- | --------------------------------------------- |
| `src/erk/cli/commands/exec/scripts/objective_roadmap_update.py` | 15      | `import click as cl`                          |
| `src/erk/tui/screens/...`                                       | Various | `from textual.app import ComposeResult as CR` |
| `tests/...`                                                     | Various | `import pytest as pt` (common in test files)  |

## Distinguishing Re-Exports from Aliases

**Re-export pattern** (`import X as X`):

```python
# This is ALLOWED — explicit re-export marker
import foo as foo

# Typically used in __init__.py to control public API:
from .internal import Widget as Widget  # Explicit re-export
```

**Detection**: Use negative lookahead `(?!\1\b)` to reject matches where alias equals module name.

**Implementation**:

```python
# The pattern automatically excludes re-exports
pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
#                                    ^^^^^^
#                                    This makes "import X as X" NOT match
```

## Pre-Commit Hook Integration

This pattern can be used in pre-commit hooks to prevent new violations:

```bash
#!/bin/bash
# .git/hooks/pre-commit

cat <<'EOF' > /tmp/check_import_aliases.py
import re
import sys
from pathlib import Path

pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
violations = []

for file_path in sys.argv[1:]:
    content = Path(file_path).read_text()
    for line_num, line in enumerate(content.splitlines(), start=1):
        if re.match(pattern, line):
            violations.append(f"{file_path}:{line_num}: {line.strip()}")

if violations:
    print("Import alias violations detected:")
    print("\n".join(violations))
    sys.exit(1)
EOF

python /tmp/check_import_aliases.py $(git diff --cached --name-only --diff-filter=ACM | grep '\.py$')
```

## Related Documentation

- [Bash-Python Integration](../architecture/bash-python-integration.md) — Escaping regex patterns in bash heredocs
- [Dignified Python Standards](../../AGENTS.md#python-standards) — Complete no-import-aliases rule rationale
