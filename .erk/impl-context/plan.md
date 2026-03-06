# Fix Dignified Python False Positives: Assert in Tests & Library Import Aliases

## Context

Users report two false positives from the Dignified Python code review:
1. `assert` in test code is flagged as a violation — but `assert` is the standard pytest assertion mechanism and should be fine in all test code
2. Common library-level import aliases like `import dagster as dg`, `import pandas as pd`, `import numpy as np` are flagged — but these are well-established community conventions

## Changes

### 1. Update assert rule in `dignified-python-core.md` (line ~86-103)

Current rule: `assert` is only acceptable for type narrowing after a guard check.

**Change**: Add that `assert` is always acceptable in test code (`test_*.py`, `*_test.py`, `conftest.py`). The type-narrowing restriction only applies to production code.

### 2. Update import alias rule in `dignified-python-core.md` (line ~202-222)

Current rule: `as` keyword for aliasing is prohibited except for name collisions.

**Change**: Add a second exception for well-known library-level aliases that are community conventions (e.g., `import pandas as pd`, `import numpy as np`, `import dagster as dg`, `import matplotlib.pyplot as plt`). The rule still prohibits gratuitous renaming of internal/project imports.

### 3. Update review prompt in `.erk/reviews/dignified-python.md` (line ~85-86)

Update the LBYL rule exception note (line 85-86) to also mention that `assert` is unrestricted in test files.

Add an exception note for the import alias rule mentioning well-known library aliases.

## Files to Modify

- `.claude/skills/dignified-python/dignified-python-core.md` — core rules (assert section + import alias section)
- `.erk/reviews/dignified-python.md` — review prompt exceptions

## Verification

- Read through both files after edits to confirm clarity
- Confirm the examples make the boundaries clear (library aliases OK, project-internal aliases still flagged)
