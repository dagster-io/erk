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
---

# Kit Artifact and Symlink Management

This guide documents the kit artifact system architecture and common pitfalls.

## Architecture Overview

```
BUNDLED KIT SOURCE                    INSTALLED ARTIFACTS
(packages/dot-agent-kit/              (project/.claude/)
 data/kits/<kit-name>/)

kit.yaml (manifest)          -->      Listed in dot-agent.toml
skills/foo/SKILL.md          -->      .claude/skills/foo/SKILL.md (symlink to source)
docs/bar/guide.md            -->      .claude/docs/bar/guide.md (symlink to source)
```

**Key Insight**: Installed artifacts are symlinks pointing TO bundled kit sources, NOT copies.

## CRITICAL: Do NOT Use Symlinks in Bundled Kit Sources

**WRONG** (causes circular symlink problems during sync):

```
# In packages/dot-agent-kit/data/kits/my-kit/
docs/foo.md -> ../../../../../.claude/docs/foo.md  # BAD - symlink in kit source
```

**RIGHT** (real files in kit source):

```
# In packages/dot-agent-kit/data/kits/my-kit/
docs/foo.md  # Real file content lives here
```

The installation process creates symlinks FROM `.claude/` TO the bundled kit. If the bundled kit already contains symlinks pointing to `.claude/`, you get circular references.

## Adding Docs to a Kit

### If docs already exist in `.claude/docs/` (project-level)

**Option 1: Move to Kit (Recommended)**

1. Copy files from `.claude/docs/<name>/` to `packages/.../kits/<kit>/docs/<name>/`
2. Add paths to `kit.yaml` under `artifacts: doc:`
3. Delete the original files from `.claude/docs/`
4. Run `dot-agent kit sync --force` to recreate symlinks

**Option 2: Reference External Docs**
If the docs are shared across multiple kits or shouldn't be bundled:

- Don't add them to kit.yaml
- Accept that kit-check will show them as "not in kit artifacts"
- The @ references will still work at runtime since `.claude/docs/` exists

### If creating new docs for a kit

1. Create the file directly in `packages/.../kits/<kit>/docs/<path>/`
2. Add the path to `kit.yaml` under `artifacts: doc:`
3. Run `dot-agent kit sync --force` to install

## Why "kit sync" Says "Up to Date" But Artifacts Are Missing

`kit sync` uses version comparison. It only syncs if:

- Kit version in manifest > installed version
- OR `--force` flag is used

**If you added new artifacts without bumping version:**

```bash
dot-agent kit sync --force  # Required to pick up new artifacts
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

## Related Documentation

- [Artifact Synchronization](artifact-synchronization.md) - Version-based sync behavior
- [Kit CLI Commands](cli-commands.md) - Available kit management commands
