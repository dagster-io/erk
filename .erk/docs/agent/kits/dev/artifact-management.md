---
title: Kit Artifact Build System
read_when:
  - "adding artifacts to kits"
  - "fixing kit-check errors"
  - "running kit-build command"
  - "understanding kit artifact architecture"
tripwires:
  - action: "editing artifacts without running kit-build"
    warning: "After editing source files (.claude/, .erk/docs/kits/, .github/), run `erk dev kit-build` to sync changes to kit packages."
  - action: "editing artifact files in kit packages instead of source locations"
    warning: "Kit packages are BUILD OUTPUTS. Edit source files in .claude/, .erk/docs/kits/, or .github/workflows/, then run `erk dev kit-build`."
---

# Kit Artifact Build System

This guide documents the kit artifact architecture and build workflow.

## Architecture Overview

```
SOURCE LOCATIONS (source of truth)        BUILT OUTPUT
(.claude/, .erk/docs/kits/,              (packages/erk-kits/
 .github/workflows/)                      data/kits/<kit-name>/)

.claude/skills/foo/SKILL.md         -->   skills/foo/SKILL.md (copy)
.erk/docs/kits/bar/guide.md         -->   docs/bar/guide.md (copy)
.github/workflows/baz.yml           -->   workflows/baz.yml (copy)
```

**Key Insight**: Source locations are the source of truth. Kit packages contain built artifacts copied via `erk dev kit-build`.

## Directory-Based Discovery

Artifacts are discovered by scanning source directories for all markdown files.
All artifacts from source directories are included in the built kit.

Source directories:

- `.claude/commands/` - Command artifacts
- `.claude/skills/` - Skill artifacts
- `.claude/agents/` - Agent artifacts
- `.erk/docs/kits/` - Documentation artifacts

## Development Workflow

### Editing Existing Artifacts

1. **Edit the source file** in `.claude/`, `.erk/docs/kits/`, or `.github/workflows/`
2. **Run build**: `erk dev kit-build`
3. **Commit both** the source file AND the built output in kit packages

### Adding New Artifacts

1. **Create the source file** in the appropriate location:
   - Commands → `.claude/commands/<namespace>/`
   - Skills → `.claude/skills/<name>/SKILL.md`
   - Agents → `.claude/agents/`
   - Kit docs → `.erk/docs/kits/<path>/`
2. **Run build**: `erk dev kit-build`
3. **Commit all changes**

## The `kit-build` Command

```bash
# Build all kits
erk dev kit-build

# Build specific kit
erk dev kit-build --kit erk

# Check for drift without building (CI mode)
erk dev kit-build --check

# Verbose output
erk dev kit-build --verbose
```

### Options

| Option      | Description                                  |
| ----------- | -------------------------------------------- |
| `--kit`     | Build only the specified kit                 |
| `--check`   | Verify artifacts are in sync (exit 1 if not) |
| `--verbose` | Show detailed output of what's being copied  |

## CI Integration

The Makefile provides targets for CI:

```bash
# Build all kit artifacts
make kit-build

# Check for artifact drift (fails if out of sync)
make kit-build-check
```

### CI Workflow

1. Developer edits source file
2. Developer runs `erk dev kit-build`
3. Developer commits source AND built output
4. CI runs `make kit-build-check` to verify sync

If CI fails with "kit artifacts out of sync", the developer forgot to run `kit-build` after editing source files.

## Troubleshooting

### Problem: Built artifact doesn't appear in kit package

**Cause**: File path doesn't match expected source locations
**Fix**: Ensure source file is in `.claude/`, `.erk/docs/kits/`, or `.github/workflows/`

### Problem: CI fails with "artifacts out of sync"

**Cause**: Source files were edited but `kit-build` wasn't run
**Fix**: Run `erk dev kit-build` and commit the updated kit packages

## Related Documentation

- [Build System Details](build-system.md) - Detailed build system architecture
- [Kit CLI Commands](cli-commands.md) - Available kit management commands
