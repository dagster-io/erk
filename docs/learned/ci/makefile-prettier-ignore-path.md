---
title: Makefile Prettier Ignore Path
read_when:
  - "modifying Prettier configuration"
  - "creating .prettierignore file"
  - "working with Makefile format target"
tripwires:
  - score: 4
    action: "Creating or modifying .prettierignore"
    warning: "The Makefile uses `prettier --ignore-path .gitignore`, NOT `.prettierignore`. Adding rules to .prettierignore has no effect. Modify .gitignore to control what Prettier ignores."
    context: "This design keeps ignore patterns DRY - files ignored by git are also ignored by Prettier. Prettier's default .prettierignore support is bypassed by the --ignore-path flag."
---

# Makefile Prettier Ignore Path

## The Pattern

Erk's Makefile configures Prettier to use `.gitignore` instead of `.prettierignore`:

```makefile
.PHONY: format-prettier
format-prettier:
	prettier --write --ignore-path .gitignore "**/*.{ts,tsx,js,jsx,json,md,yml,yaml}"
```

## Why --ignore-path .gitignore

This design choice has several benefits:

1. **DRY (Don't Repeat Yourself)**: Files ignored by git should also be ignored by formatters
2. **Single source of truth**: One file controls what's ignored across multiple tools
3. **Simpler maintenance**: No need to sync .gitignore and .prettierignore
4. **Consistent behavior**: Developers don't see formatting errors in files they can't commit

## What This Means

- **`.prettierignore` is unused**: Creating this file has no effect on formatting
- **Modify `.gitignore` instead**: To ignore files from Prettier, add patterns to .gitignore
- **Build artifacts auto-ignored**: Since dist/, .venv/, etc. are in .gitignore, Prettier skips them

## Common Scenarios

### "I want to ignore a directory from Prettier but not git"

This is intentionally not supported. The design assumes:

- If a file should be committed, it should be formatted
- If a file shouldn't be formatted, it shouldn't be committed

If you have a legitimate use case for this, consider:

1. Is the file actually needed in the repository?
2. Should it be a generated/build artifact instead?
3. Could it live outside the repository?

### "I want to format files that are gitignored"

Remove the pattern from .gitignore, or use `prettier` directly without the Makefile target:

```bash
# Format specific gitignored file
prettier --write path/to/file.md
```

## Related Patterns

- `.gitignore` - Single source of truth for ignored files
- `Makefile` - All formatting and linting targets
- [CI Workflow Patterns](../ci/workflow-gating-patterns.md) - How formatting checks run in CI

## Attribution

Pattern used since project inception, consolidated during Docker/Codespace removal (PR #6359).
