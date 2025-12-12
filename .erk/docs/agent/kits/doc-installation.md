---
title: Kit Documentation Installation Architecture
read_when:
  - "understanding where kit documentation gets installed"
  - "adding documentation to a kit"
  - "wondering why docs are in .erk instead of .claude"
  - "creating @ references to kit documentation"
---

# Kit Documentation Installation Architecture

Kit documentation is installed to `.erk/docs/kits/<kit-id>/` (not `.claude/docs/<kit>/`).

## Directory Structure

```
.erk/docs/kits/
├── dignified-python/
│   ├── dignified-python-core.md
│   ├── type-annotations-common.md
│   └── version-specific/
│       ├── 310/
│       ├── 311/
│       ├── 312/
│       └── 313/
├── erk/
│   └── includes/
│       └── conflict-resolution.md
└── devrun/
    └── ...
```

## Why `.erk/` Instead of `.claude/`

1. **Separation of concerns** - `.claude/` contains user-facing artifacts (commands, skills, hooks) that appear in the Claude Code UI
2. **Hidden by default** - Kit documentation is reference material for skills/commands, not a primary interface users interact with
3. **Organized by kit** - Each kit's docs are namespaced under its kit ID, preventing conflicts between kits

## @ Reference Syntax

From installed skills and commands, reference kit docs using absolute paths from project root:

```markdown
@.erk/docs/kits/dignified-python/dignified-python-core.md
```

For relative references from within a skill to its kit's docs:

```markdown
@../../.erk/docs/kits/dignified-python/type-annotations-common.md
```

## Installation Flow

1. Kit manifest (`kit.yaml`) declares docs under `artifacts: doc:`
2. Source files live in `packages/erk-kits/data/kits/<kit>/docs/`
3. Installation creates symlinks from `.erk/docs/kits/<kit>/` to source
4. Skills/commands use @ references that resolve at runtime

## Key Distinction from `.claude/docs/`

If a project has its own documentation in `.claude/docs/`, these are:

- **Not kit-managed** - They're project-specific, user-created docs
- **Different location** - Kit docs go to `.erk/docs/kits/`, not `.claude/docs/`
- **No conflict** - The paths are completely separate

## Related Documentation

- [Artifact Path Transformation](artifact-path-transformation.md) - How paths are transformed during installation
- [Kit Artifact and Symlink Management](dev/artifact-management.md) - Symlink handling during installation
