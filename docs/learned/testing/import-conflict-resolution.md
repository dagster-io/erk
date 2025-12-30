---
title: Merge Conflict Resolution for Import Consolidation
read_when:
  - "resolving merge conflicts during rebase"
  - "fixing import conflicts after consolidation"
  - "rebasing after shared module changes"
---

# Merge Conflict Resolution for Import Consolidation

When import paths are consolidated into shared modules, rebasing other branches can cause merge conflicts. This guide covers the resolution strategy.

## Common Scenario

You consolidated imports in one branch:

```python
# Before: multiple local helpers
from .local_helpers import parse_url

# After: shared module
from erk_shared.github.parsing import parse_url
```

When rebasing other branches that still use the old imports, conflicts appear.

## Resolution Strategy

### Step 1: Identify the Conflict Type

Conflict markers typically look like:

```python
<<<<<<< HEAD
from erk_shared.github.parsing import parse_pr_number, parse_issue_number
=======
from .github_helpers import parse_pr_number
from .issue_helpers import parse_issue_number
>>>>>>> feature-branch
```

### Step 2: Verify Shared Module Exists

Before resolving, confirm the shared module has the functions:

```bash
grep -n "def parse_pr_number" src/erk_shared/github/parsing.py
```

### Step 3: Prefer HEAD's Shared Imports

If the shared module exists and has the functions, use HEAD's version:

```python
# Resolution: use the consolidated import
from erk_shared.github.parsing import parse_pr_number, parse_issue_number
```

### Step 4: Remove Obsolete Local Helpers

If the feature branch created local helper files that are now obsolete:

```bash
git rm src/erk/cli/local_helpers.py
```

### Step 5: Complete the Rebase

```bash
git add .
gt continue
# or: git rebase --continue
```

## Decision Framework

| Situation                       | Resolution                         |
| ------------------------------- | ---------------------------------- |
| Function exists in shared       | Use shared import (HEAD)           |
| Function only in feature branch | Add to shared module, then resolve |
| Feature branch has local helper | Delete helper, use shared          |
| Both have different impls       | Merge into shared, use shared      |

## Example: Full Resolution

Starting conflict:

```python
<<<<<<< HEAD
from erk_shared.github.parsing import (
    parse_pr_number,
    parse_issue_number,
    parse_repo_from_url,
)
=======
from .github_url_parser import parse_pr_number
from .issue_parser import parse_issue_number
>>>>>>> add-repo-parsing
```

Resolution:

```python
from erk_shared.github.parsing import (
    parse_pr_number,
    parse_issue_number,
    parse_repo_from_url,
)
```

Then verify no references to deleted modules remain:

```bash
grep -r "from .github_url_parser" src/
grep -r "from .issue_parser" src/
```

## Common Pitfalls

1. **Don't preserve both imports** - This creates duplicate imports or shadows
2. **Don't forget to delete local helpers** - They become dead code
3. **Verify function signatures match** - Shared module may have updated signatures

## Related Topics

- [Rebase Conflicts](rebase-conflicts.md) - ErkContext API changes during rebase
- [Architecture](../architecture/) - Understanding two-layer architecture
