---
title: Kit Artifact and Symlink Management
read_when:
  - "adding artifacts to kits"
  - "fixing kit-check errors"
  - "troubleshooting kit sync"
  - "kit sync says up to date but artifacts missing"
tripwires:
  - action: "creating symlinks in bundled kit source directories"
    warning: "Bundled kits should contain real files, NOT symlinks. The installation process creates symlinks FROM .claude/ TO kit sources."
  - action: "running `kit sync` after adding artifacts to kit.yaml"
    warning: "Must use `--force` flag if version wasn't bumped."
  - action: "editing files in .claude/ that are symlinks to kit sources"
    warning: "Kit artifacts in .claude/ are symlinks. Edit the SOURCE file in the kit package (use `readlink -f` to find it), or the symlink will be replaced with a regular file."
---

# Kit Artifact and Symlink Management

This guide documents the kit artifact system architecture and common pitfalls.

## Architecture Overview

```
BUNDLED KIT SOURCE                    INSTALLED ARTIFACTS
(packages/erk-kits/              (project/.claude/)
 data/kits/<kit-name>/)

kit.yaml (manifest)          -->      Listed in kits.toml
skills/foo/SKILL.md          -->      .claude/skills/foo/SKILL.md (symlink to source)
docs/bar/guide.md            -->      .claude/docs/bar/guide.md (symlink to source)
```

**Key Insight**: Installed artifacts are symlinks pointing TO bundled kit sources, NOT copies.

## CRITICAL: Do NOT Use Symlinks in Bundled Kit Sources

**WRONG** (causes circular symlink problems during sync):

```
# In packages/erk-kits/data/kits/my-kit/
docs/foo.md -> ../../../../../.claude/docs/foo.md  # BAD - symlink in kit source
```

**RIGHT** (real files in kit source):

```
# In packages/erk-kits/data/kits/my-kit/
docs/foo.md  # Real file content lives here
```

The installation process creates symlinks FROM `.claude/` TO the bundled kit. If the bundled kit already contains symlinks pointing to `.claude/`, you get circular references.

## Adding Docs to a Kit

### If docs already exist in `.claude/docs/` (project-level)

**Option 1: Move to Kit (Recommended)**

1. Copy files from `.claude/docs/<name>/` to `packages/.../kits/<kit>/docs/<name>/`
2. Add paths to `kit.yaml` under `artifacts: doc:`
3. Delete the original files from `.claude/docs/`
4. Run `erk kit sync --force` to recreate symlinks

**Option 2: Reference External Docs**
If the docs are shared across multiple kits or shouldn't be bundled:

- Don't add them to kit.yaml
- Accept that kit-check will show them as "not in kit artifacts"
- The @ references will still work at runtime since `.claude/docs/` exists

### If creating new docs for a kit

1. Create the file directly in `packages/.../kits/<kit>/docs/<path>/`
2. Add the path to `kit.yaml` under `artifacts: doc:`
3. Run `erk kit sync --force` to install

## Why "kit sync" Says "Up to Date" But Artifacts Are Missing

`kit sync` uses version comparison. It only syncs if:

- Kit version in manifest > installed version
- OR `--force` flag is used

**If you added new artifacts without bumping version:**

```bash
erk kit sync --force  # Required to pick up new artifacts
```

## Troubleshooting

### Problem: kit-check shows missing @ references

**Cause**: Artifact file is referenced in skill/command markdown but not listed in kit.yaml
**Fix**: Add the file path to the `artifacts:` section of kit.yaml

### Problem: Symlinks are circular (file -> file)

**Cause**: Bundled kit source contains symlinks instead of real files
**Fix**: Replace symlinks in kit source with actual file content

### Problem: File exists but kit-check says missing

**Cause**: Path in kit.yaml doesn't match actual file location
**Fix**: Verify the path in kit.yaml exactly matches the relative path from kit root

### Problem: Relative @ references (../../path) not resolving

**Cause**: kit-check resolves relative paths from artifact location
**Fix**: Ensure the referenced file exists at the resolved path

## Editing Kit Artifacts

When you need to edit a file in `.claude/` that's part of an installed kit, **you must edit the source file**, not the symlink path.

### Why This Matters

Installed kit artifacts in `.claude/` are **symlinks** pointing to source files in the kit package:

```
.claude/skills/foo/SKILL.md -> packages/erk-kits/data/kits/bar/skills/foo/SKILL.md
```

If you use Write tool on `.claude/skills/foo/SKILL.md`:

1. Write tool deletes the existing file (removes the symlink)
2. Creates a new regular file with the content
3. Git sees `typechange: link -> file` — the symlink is now a regular file

This breaks the kit architecture because:

- The source file in the kit package is unchanged
- `kit sync` will overwrite your changes (or create conflicts)
- Other projects using this kit won't get your changes

### How to Identify Kit Symlinks

Check if a `.claude/` file is a symlink:

```bash
# See if file is a symlink
ls -la .claude/skills/foo/SKILL.md
# Output: .claude/skills/foo/SKILL.md -> packages/.../SKILL.md

# Or use file command
file .claude/skills/foo/SKILL.md
# Output: symbolic link to packages/.../SKILL.md
```

### Correct Workflow for Editing Kit Artifacts

1. **Find the source file**:

   ```bash
   readlink -f .claude/skills/foo/SKILL.md
   # Output: /path/to/packages/erk-kits/data/kits/bar/skills/foo/SKILL.md
   ```

2. **Edit the source file** (not the symlink path):

   ```bash
   # Use Read tool on the resolved path
   # Use Edit tool on the resolved path
   ```

3. **Verify symlink is intact**:
   ```bash
   ls -la .claude/skills/foo/SKILL.md
   # Should still show symlink, not regular file
   ```

### What If You Already Broke a Symlink?

If `git status` shows `typechange` for a `.claude/` file:

1. Check out the original symlink: `git checkout -- .claude/path/to/file`
2. Find the source file: `readlink -f .claude/path/to/file`
3. Apply your changes to the source file
4. Verify the symlink is restored: `ls -la .claude/path/to/file`

## Related Documentation

- [Artifact Synchronization](artifact-synchronization.md) - Version-based sync behavior
- [Kit CLI Commands](cli-commands.md) - Available kit management commands
