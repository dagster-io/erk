---
title: Kit Check Command
read_when:
  - "validating kit configuration"
  - "debugging missing artifacts"
tripwire: false
---

# Kit Check Command

Validates that all artifacts referenced in kit configuration files exist.

## Usage

```bash
dot-agent dev kit-check [--kit KIT_NAME] [--verbose]
```

## What It Validates

1. **Kit Registry** (`.agent/kits/kit-registry.md`)
   - All kits listed exist in the kits directory
   - Kit metadata is properly formatted

2. **Kit Configuration** (`.agent/kits/<kit>/kit.toml`)
   - All artifact references point to existing files
   - Artifact types are valid (skill, command, agent, hook, doc)

3. **Artifact Files**
   - Referenced files exist at expected paths
   - File types match declared artifact types

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

- After modifying kit configuration
- Before committing kit changes
- During CI to catch broken references
