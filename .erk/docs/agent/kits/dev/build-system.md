---
title: Kit Build System Architecture
read_when:
  - "understanding how kit-build works internally"
  - "debugging kit build failures"
  - "extending the kit build system"
---

# Kit Build System Architecture

This document describes the detailed architecture of the kit artifact build system.

## Overview

The kit build system implements a **source-to-package** workflow:

1. **Source locations** (`.claude/`, `.erk/docs/kits/`, `.github/workflows/`) are the source of truth
2. **Build command** (`erk dev kit-build`) copies source files to kit packages
3. **Kit packages** (`packages/erk-kits/data/kits/<name>/`) contain built artifacts

This inverts the traditional model where kit packages were source and `.claude/` contained symlinks.

## Source Location Discovery

The build system scans these directories for kit artifacts:

| Directory            | Artifact Type | Kit Package Destination |
| -------------------- | ------------- | ----------------------- |
| `.claude/skills/`    | Skills        | `skills/`               |
| `.claude/commands/`  | Commands      | `commands/`             |
| `.claude/hooks/`     | Hooks         | `hooks/`                |
| `.claude/agents/`    | Agents        | `agents/`               |
| `.erk/docs/kits/`    | Documentation | `docs/`                 |
| `.github/workflows/` | Workflows     | `workflows/`            |

## Frontmatter-Based Kit Assignment

Each source file declares its kit ownership via YAML frontmatter:

```yaml
---
erk.kit: <kit-name>
---
```

### Processing Rules

1. Files without `erk.kit` field are **skipped** (project-local artifacts)
2. Files with unknown kit names cause **errors**
3. The frontmatter is **preserved** in the built output

### Why Frontmatter?

Previous approaches had drawbacks:

- **Path-based**: Required rigid directory structures
- **Manifest-based**: Required maintaining separate artifact lists
- **Convention-based**: Ambiguous when multiple kits exist

Frontmatter provides:

- Self-documenting source files
- Flexible directory organization
- Clear kit ownership at a glance

## Build Process

### Step 1: Source Discovery

```
Scan source directories → Filter by frontmatter → Group by kit
```

### Step 2: Kit Package Sync

For each kit:

```
For each source file with erk.kit: <this-kit>:
    dest = kit_package / artifact_type / relative_path
    copy(source, dest)
```

### Step 3: Staleness Check

```
For each file in kit package:
    if no corresponding source file with erk.kit: <this-kit>:
        warn("stale artifact")
```

## Check Mode (`--check`)

In check mode, the build system:

1. Computes what **would** be copied
2. Compares against current kit package state
3. Reports drift without making changes
4. Exits with code 1 if out of sync

Used in CI to enforce "source + built output" commit discipline.

## When kit-build Runs

Understanding when `kit-build` is and isn't invoked:

| Context              | kit-build invoked? | Notes                                |
| -------------------- | ------------------ | ------------------------------------ |
| Developer workflow   | **Manual**         | Run after editing source files       |
| `make fast-ci`       | ✅ Yes             | Runs build, then `--check` to verify |
| `make all-ci`        | ✅ Yes             | Runs build, then `--check` to verify |
| `make publish`       | ❌ No              | Assumes artifacts already in sync    |
| `make build`         | ❌ No              | Only runs `uv build` for packages    |
| Git pre-commit hooks | ❌ No              | Not currently integrated             |

**Key insight**: The publish process does NOT automatically run `kit-build`. It assumes developers have already run the build and committed both source and built output. CI catches drift but doesn't auto-fix.

### Recommended Workflow

1. Edit source files in `.claude/`, `.erk/docs/kits/`, etc.
2. Run `erk dev kit-build`
3. Commit both source AND built output together
4. CI validates sync via `kit-build --check`

## Command Options

```bash
erk dev kit-build [OPTIONS]
```

| Option       | Description                     |
| ------------ | ------------------------------- |
| `--kit NAME` | Build only specified kit        |
| `--check`    | Verify sync without modifying   |
| `--verbose`  | Show detailed copy operations   |
| `--dry-run`  | Preview changes without writing |

## Error Handling

### Missing Frontmatter

```
ERROR: .claude/skills/foo/SKILL.md missing erk.kit frontmatter
```

**Resolution**: Add `erk.kit: <kit-name>` to file's YAML frontmatter.

### Unknown Kit

```
ERROR: .claude/skills/foo/SKILL.md has erk.kit: invalid-kit (not found)
```

**Resolution**: Check `packages/erk-kits/data/kits/` for valid kit names.

### Stale Artifact

```
WARN: packages/erk-kits/data/kits/foo/skills/old/SKILL.md has no source
```

**Resolution**: Delete the stale file from the kit package, or restore its source.

## Integration with kit.yaml

The `kit.yaml` manifest in each kit package lists artifacts for installation:

```yaml
artifacts:
  skill:
    - skills/foo/SKILL.md
  doc:
    - docs/guide/index.md
```

**Important**: `kit-build` copies files but does NOT update kit.yaml. New artifacts must be manually added to the manifest.

## Related Documentation

- [Kit Artifact Management](artifact-management.md) - Overview and workflows
- [Kit CLI Commands](cli-commands.md) - All kit-related commands
