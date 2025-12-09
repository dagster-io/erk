---
title: Kit Check Command
read_when:
  - "validating kit configuration"
  - "debugging missing artifacts"
  - "kit-check errors"
tripwire: false
---

# Kit Check Command

Validates that all artifacts referenced in kit configuration files exist and that @ references in kit artifacts resolve correctly.

## Usage

```bash
dot-agent dev kit-check [--kit KIT_NAME] [--verbose]
```

## What It Validates

### 1. Kit Registry (`.erk/kits/kit-registry.md`)

- All kits listed exist in the kits directory
- Kit metadata is properly formatted

### 2. Kit Configuration (`.erk/kits/<kit>/kit.toml` or `kit.yaml`)

- All artifact references point to existing files
- Artifact types are valid (skill, command, agent, hook, doc)

### 3. Artifact Files

- Referenced files exist at expected paths
- File types match declared artifact types

### 4. @ Reference Resolution

- All `@path/to/file.md` references in kit artifacts resolve to existing files
- Relative paths are resolved from the artifact's location

## Options

| Flag             | Description                                      |
| ---------------- | ------------------------------------------------ |
| `--kit KIT_NAME` | Check only the specified kit                     |
| `--verbose`      | Show detailed output including all checked files |

## Example Output

```
$ dot-agent dev kit-check

Checking kit: erk
  [ok] skills/erk/skill.md
  [ok] commands/erk-wt-create.md
  [MISSING] hooks/erk-post-checkout.md

Checking kit: dignified-python
  [ok] skills/dignified-python-313/skill.md
  [ok] docs/dignified-python/core.md

Summary: 1 error, 0 warnings
```

## When to Run

- **After modifying kit configuration** - Catch broken references before committing
- **Before committing kit changes** - Ensure all artifacts are properly linked
- **During CI** - Automated validation of kit integrity
- **After running `kit sync`** - Verify symlinks were created correctly

## Common Issues

### Missing @ Reference

```
[ERROR] Missing @ reference in skills/erk/skill.md:
  @docs/agent/erk/workflows.md → File not found
```

**Fix**: Either create the referenced file or update the @ reference path.

### Artifact Not in Kit

```
[WARNING] File referenced but not in kit.yaml:
  docs/agent/erk/custom.md
```

**Fix**: Add the file path to the `artifacts:` section of kit.yaml.

### Invalid Artifact Type

```
[ERROR] Invalid artifact type 'foo' in kit.yaml
  Valid types: skill, command, agent, hook, doc
```

**Fix**: Use one of the valid artifact types.

## Related Documentation

- [Artifact Management](artifact-management.md) - How kit artifacts work
- [Kit CLI Commands](cli-commands.md) - All kit management commands
