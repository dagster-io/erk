# Diff Analysis Guide

Shared instructions for analyzing git diffs and generating commit messages.

## Analysis Principles

**Analyze the diff following these principles:**

- **Be concise and strategic** - focus on significant changes
- **Use component-level descriptions** - reference modules/components, not individual functions
- **Highlight breaking changes prominently**
- **Note test coverage patterns**
- **Use relative paths from repository root**

## Level of Detail

- Focus on architectural and component-level impact
- Keep "Key Changes" to 3-5 major items
- Group related changes together
- Skip minor refactoring, formatting, or trivial updates

## Structure Analysis Output

Create a compressed analysis with these sections:

```markdown
## Summary

[2-3 sentence high-level overview of what changed and why]

## Files Changed

### Added (X files)

- `path/to/file.py` - Brief purpose (one line)

### Modified (Y files)

- `path/to/file.py` - What area changed (component level)

### Deleted (Z files)

- `path/to/file.py` - Why removed (strategic reason)

## Key Changes

[3-5 high-level component/architectural changes]

- Strategic change description focusing on purpose and impact
- Focus on what capabilities changed, not implementation details

## Critical Notes

[Only if there are breaking changes, security concerns, or important warnings]

- [1-2 bullets max]
```

## Craft Brief Top Summary

Create a concise 2-4 sentence summary paragraph that:

- States what the branch does (feature/fix/refactor)
- Highlights the key changes briefly
- Uses clear, professional language

## Construct Commit Message

Combine the brief summary with the compressed analysis:

```
[Brief summary paragraph]

[Compressed analysis sections]
```

The message should be concise (typically 15-30 lines total) with essential information preserved.

## Important Rules

- NO Claude footer or attribution
- Use relative paths from repository root
- Avoid function-level details unless critical
- Maximum 5 key changes
- Only include Critical Notes if necessary
