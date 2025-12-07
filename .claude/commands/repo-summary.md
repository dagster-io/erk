---
description: Summarize repo contributions since a given date
---

# Repository Contribution Summary

Generate a holistic summary of contributions to the repository since a specified date.

## Arguments

- `$ARGUMENTS` - A date string (e.g., "Thursday 9 AM", "2025-12-05", "last week", "3 days ago")

## Implementation

1. **Parse the date argument** and convert to git-compatible format
2. **Find the baseline commit** (last commit before the specified date)
3. **Gather statistics** by running these commands:

```bash
# Get baseline commit
git log --oneline --before='<parsed_date>' master | head -1

# Count merged PRs (commits with PR numbers)
git log --oneline --since='<parsed_date>' master | grep -E '\(#[0-9]+\)' | wc -l

# Get all PR titles for categorization
git log --oneline --since='<parsed_date>' master | grep -E '\(#[0-9]+\)'

# Python line changes (total)
git diff --numstat <baseline> master -- '*.py' | awk '{added+=$1; deleted+=$2} END {print "Added:", added, "Deleted:", deleted, "Net:", added-deleted}'

# Python test vs src breakdown
git diff --numstat <baseline> master -- '*.py' | grep -E '(test|_test\.py|tests/)' | awk '{added+=$1; deleted+=$2} END {print "Tests - Net:", added-deleted}'
git diff --numstat <baseline> master -- '*.py' | grep -vE '(test|_test\.py|tests/)' | awk '{added+=$1; deleted+=$2} END {print "Src - Net:", added-deleted}'

# Markdown line changes
git diff --numstat <baseline> master -- '*.md' | awk '{added+=$1; deleted+=$2} END {print "Added:", added, "Deleted:", deleted, "Net:", added-deleted}'
```

4. **Categorize PRs** by analyzing commit messages:
   - **New Features**: "Add", "Implement", "Create", "Enable"
   - **Bug Fixes**: "Fix", "Resolve", "Handle", "Prevent"
   - **Documentation**: "Document", "Update.*documentation", commits touching only .md files
   - **Refactors**: "Refactor", "Consolidate", "Simplify", "Remove", "Replace", "Deprecate", "Clean up"

5. **Generate summary report** with:

### Summary Format

```
## Contributions Since <date>

### Overview
- **PRs Merged**: X
- **Python Net Lines**: +Y (Z% tests, W% source)
- **Markdown Net Lines**: +V

### By Category
| Category | Count | % |
|----------|-------|---|
| New Features | X | Y% |
| Bug Fixes | X | Y% |
| Documentation | X | Y% |
| Refactors | X | Y% |

### New Features (X)
- Feature 1
- Feature 2
...

### Bug Fixes (X)
- Fix 1
- Fix 2
...

### Documentation (X)
- Doc 1
...

### Refactors (X)
- Refactor 1
...
```

## Example Usage

```
/repo-summary Thursday 9 AM
/repo-summary 2025-12-01
/repo-summary "last week"
/repo-summary "5 days ago"
```
