---
description: Analyze merged PRs by category with net lines of code statistics
argument-hint: [since]
---

# /local:code-stats

Analyzes merged PRs and categorizes them by type (user-facing features, bug fixes, documentation, etc.) with detailed line-of-code statistics broken down by Python (non-test), Python (test), and Markdown.

## Usage

```bash
/local:code-stats                    # Default: since 2025-12-08
/local:code-stats 2025-12-01         # Since specific date
/local:code-stats "last 48 hours"    # Since 48 hours ago
/local:code-stats "last 2 weeks"     # Since 2 weeks ago
```

### Supported date formats

- **ISO date**: `2025-12-01`
- **ISO datetime**: `2025-12-01T14:30:00`
- **Relative**: `last N hour(s)`, `last N day(s)`, `last N week(s)`

## Implementation

1. **Interpret the user's input** (`$ARGUMENTS`) and convert it to an ISO datetime string:
   - "4 hours ago" / "since 4 hours ago" → subtract 4 hours from now
   - "yesterday" → yesterday's date at 00:00:00
   - "last week" → 7 days ago
   - "last 2 weeks" → 14 days ago
   - "2025-12-01" → use as-is
   - Empty/no argument → default to `2025-12-08`

2. **Run the Python script** with the ISO datetime:

```bash
python3 scripts/code_stats.py <ISO_DATETIME>
```

The Python script expects a single argument in one of these formats:

- ISO date: `2025-12-28`
- ISO datetime: `2025-12-28T14:30:00`

## Output

Produces a table like:

```
| Category                       | PRs |   %  |     Py | Py (test) | Markdown | Net LOC |   %  |
|--------------------------------|----:|-----:|-------:|----------:|---------:|--------:|-----:|
| 🚀  User-Facing Features       |  20 |  20% |   +406 |      +946 |   +2,268 |  +3,620 |  17% |
| ✨  User-Facing Improvements   |   1 |   1% |    +26 |       +98 |      +71 |    +195 |   1% |
| 🐛  Bug Fixes                  |  13 |  13% |   +528 |      +626 |     +327 |  +1,481 |   7% |
| ...                            | ... |  ... |    ... |       ... |      ... |     ... |  ... |
|--------------------------------|----:|-----:|-------:|----------:|---------:|--------:|-----:|
| **TOTAL**                      | 100 | 100% | +5,803 |    +8,759 |   +7,115 | +21,677 | 100% |
```

## Categories

Categories are determined by analyzing diff content (not just PR titles):

1. **User-Facing Features** - New slash commands, CLI commands, skills
2. **User-Facing Improvements** - Enhancements to existing user-facing features
3. **Bug Fixes** - PRs with "fix" in title and bug-related diff patterns
4. **Documentation** - PRs that only modify `.md` files
5. **Migrations/Renames** - Config migrations, renames, terminology updates
6. **Internal/Infrastructure** - Changes to ABCs, gateways, internal APIs
7. **Refactoring** - Consolidation, cleanup, standardization
8. **Other** - Everything else

## Notes

- Analyzes **merged PRs only** (not open PRs or commits)
- Line counts include only Python and Markdown files
- PRs without merge commits are counted as "Other"
