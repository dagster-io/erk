---
description: Analyze merged PRs by category with net lines of code statistics
argument-hint: [since]
context: fork
agent: general-purpose
model: sonnet
---

# /local:code-stats

Analyzes merged PRs and categorizes them by type (user-facing features, bug fixes, documentation, etc.) with detailed line-of-code statistics broken down by Python (non-test), Python (test), and Markdown.

## Usage

```bash
/local:code-stats                    # Default: last 30 days
/local:code-stats 2025-12-01         # Since specific date
/local:code-stats 01-15-2026         # Any date format works
/local:code-stats "last 2 weeks"     # Relative expressions
/local:code-stats "since January"    # Natural language
/local:code-stats "this year"        # Calendar expressions
/local:code-stats "last quarter"     # Business date ranges
```

## Implementation

1. **Interpret the user's input** (`$ARGUMENTS`) as a date expression and convert it to `YYYY-MM-DD` format. You are an LLM — use your judgment to parse any date expression the user provides. Examples:
   - `01-01-2026` → `2026-01-01`
   - `last 2 weeks` → calculate 14 days before today
   - `since January` → `2026-01-01` (current year)
   - `this year` → `2026-01-01`
   - `last quarter` → first day of previous quarter
   - `yesterday` → yesterday's date
   - `2025-12-01` → `2025-12-01`
   - Empty/no argument → 30 days ago from today

2. **Run the Python script** with the resolved `YYYY-MM-DD` date:

```bash
python3 scripts/code_stats.py <YYYY-MM-DD>
```

The script expects a single argument in `YYYY-MM-DD` format.

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
