---
title: Kit Shared Includes
read_when:
  - "sharing content between kit commands"
  - "creating reusable includes for erk kit"
  - "understanding @ reference syntax"
---

# Kit Shared Includes

Share markdown content between kit commands and skills using includes stored in `docs/erk/includes/`.

## File Location

**Path**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/docs/erk/includes/`

All shared includes live here and are referenced via `@docs/erk/includes/filename.md`.

## Naming Conventions

✅ **CORRECT**: `conflict-resolution.md`, `pr-workflow.md`, `graphite-basics.md`

❌ **WRONG**: `_conflict-resolution.md`, `internal-pr-workflow.md`

**Rules**:
- Use `kebab-case` for filenames
- No underscore prefix (all includes are "public")
- Descriptive names that indicate content

## Reference Syntax

Use `@` prefix to include files in commands or skills:

```markdown
# /erk:merge-conflicts-fix

Instructions for fixing merge conflicts.

@docs/erk/includes/conflict-resolution.md

Additional guidance...
```

## Symlink Requirements

Includes must be symlinked to `.claude/docs/erk/includes/` for agent access:

```bash
# From repo root
ln -s packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/docs/erk/includes/conflict-resolution.md \
      .claude/docs/erk/includes/conflict-resolution.md
```

**Verification**: Check symlinks exist:

```bash
ls -la .claude/docs/erk/includes/
```

## Example Include File

**File**: `docs/erk/includes/pr-workflow.md`

```markdown
## PR Submission Workflow

1. Create feature branch
2. Make changes and commit
3. Submit PR using `/gt:pr-submit` or `/git:pr-push`
4. Address review comments
5. Land PR using `/erk:pr-land`
```

## Usage in Commands

**File**: `commands/erk/pr-submit.md`

```markdown
---
description: Submit current branch as PR
---

# Submit PR

Submit your changes as a pull request.

@docs/erk/includes/pr-workflow.md

## Options

- `--draft`: Create as draft PR
- `--no-restack`: Skip rebasing stack
```

## Benefits

- **DRY**: Single source of truth for shared content
- **Consistency**: Same workflow across multiple commands
- **Maintainability**: Update once, reflect everywhere
- **Discoverability**: Centralized includes directory

## Related Documentation

- [Kit Artifact Dev Mode](dev/artifact-dev-mode.md) - Adding artifacts in dev mode
- [Kit CLI Dependency Injection](dependency-injection.md) - Context injection patterns
