---
title: Kit Artifact Synchronization Guide
read_when:
  - "adding commands to kits"
  - "removing kit commands"
  - "test_check_command_perfect_sync fails"
  - "kit manifest validation errors"
---

# Kit Artifact Synchronization Guide

This guide explains how kit artifacts (commands, tools) stay synchronized with kit manifests and how to properly add or remove kit commands.

## Understanding Kit Bundling

Kits bundle commands and tools together. The bundling system validates that:

1. Every command in the manifest has a corresponding artifact file
2. Every artifact file is declared in the manifest
3. No "orphan" artifacts exist (files without manifest entries)

## The Sync Test

The test `test_check_command_perfect_sync_no_missing_no_obsolete` validates:

```python
def test_check_command_perfect_sync_no_missing_no_obsolete():
    """Verify kit manifest matches actual artifacts."""
    kit = load_kit("my-kit")

    # Check for missing artifacts (declared but not present)
    missing = kit.get_missing_artifacts()
    assert not missing, f"Missing artifacts: {missing}"

    # Check for obsolete artifacts (present but not declared)
    obsolete = kit.get_obsolete_artifacts()
    assert not obsolete, f"Obsolete artifacts: {obsolete}"
```

## Common Sync Errors

### "Missing Artifacts" Error

**Cause:** Manifest declares a command that doesn't exist.

```
Missing artifacts: ['commands/old-command.md']
```

**Fix:** Either:

1. Create the missing artifact file, OR
2. Remove the entry from the manifest

### "Obsolete Artifacts" Error

**Cause:** Artifact file exists but isn't in manifest.

```
Obsolete artifacts: ['commands/orphan-command.md']
```

**Fix:** Either:

1. Add the artifact to the manifest, OR
2. Delete the orphan file

## Proper Command Removal Process

When removing a kit command, follow this checklist:

1. **Remove from manifest** - Delete the command entry from `kit.yaml`
2. **Delete artifact file** - Remove the command's `.md` file
3. **Update \_\_init\_\_.py** - Remove any imports/exports
4. **Update tests** - Remove tests for the command
5. **Run sync test** - Verify: `pytest tests/test_kit_sync.py -v`

### Example: Removing `my-command`

```bash
# 1. Edit kit manifest
vim src/kits/my-kit/kit.yaml
# Remove: - commands/my-command.md

# 2. Delete artifact
rm src/kits/my-kit/commands/my-command.md

# 3. Update exports (if any)
vim src/kits/my-kit/__init__.py

# 4. Remove tests
rm tests/kits/my-kit/test_my_command.py

# 5. Verify sync
pytest tests/test_kit_sync.py -v
```

## Adding New Commands

When adding a kit command:

1. **Create artifact file** - Add `.md` file in `commands/`
2. **Add to manifest** - Add entry in `kit.yaml`
3. **Add tests** - Create test file
4. **Run sync test** - Verify synchronization

## Troubleshooting

### Multiple Agents Editing Same Kit

If multiple agents modify the same kit concurrently:

- One may add while another removes
- Sync errors appear after merge
- Resolution: Re-run sync after merge, fix inconsistencies

### Test Failures After Rebase

After rebasing, kit artifacts may desync:

1. Check `git status` for conflicted kit files
2. Resolve manifest vs artifact conflicts
3. Re-run sync test

## Related Documentation

- [Kit Architecture](code-architecture.md)
- [Kit CLI Commands](cli-commands.md)
