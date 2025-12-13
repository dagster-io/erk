# Kit Documentation Registry

## Overview

The kit documentation registry provides a lightweight indexing system for installed kit artifacts. It requires only a ONE-TIME edit to AGENTS.md and automatically maintains synchronization with kit installations.

## Architecture

- **Registry file**: `.agent/kits/kit-registry.md` - Aggregates kit entries via @-includes
- **Kit entries**: `.agent/kits/<kit-id>/registry-entry.md` - One per installed kit
- **Integration**: Automatic updates during `kit install`, `kit remove`, `kit update`

## How It Works

### ONE-TIME Setup

The system requires a single addition to AGENTS.md (already done):

```markdown
## Installed Kit Documentation

For a complete index of installed kit documentation (agents, commands, skills, and reference docs), see:

@.agent/kits/kit-registry.md

This registry is automatically updated when kits are installed, updated, or removed.
```

After this ONE-TIME edit, no further manual intervention is needed.

### Automatic Maintenance

The registry is automatically maintained by kit commands:

- **`erk kit install <kit-id>`**: Generates registry entry and adds @-include
- **`erk kit remove <kit-id>`**: Removes registry entry and @-include
- **`erk kit update <kit-id>`**: Regenerates registry entry with new version

### Registry Structure

The registry uses a two-level structure to minimize context window usage:

1. **Main registry** (`.agent/kits/kit-registry.md`): Contains only @-includes for each kit
2. **Kit entries** (`.agent/kits/<kit-id>/registry-entry.md`): Contain 15-20 line summaries

This design ensures that:

- Main agent loads only a compact index at startup
- Full kit documentation is loaded on-demand when needed
- Registry stays synchronized with installed kits automatically

## Registry Entry Format

Each kit entry must include:

- **Header**: `### kit-name (vX.Y.Z)`
- **Purpose**: Brief description of what the kit provides
- **Artifacts**: List of agents, commands, skills, docs by type
- **Usage**: Example invocations for each artifact type

Example:

```markdown
### devrun (v0.1.0)

**Purpose**: Consolidated development tool runner agent with integrated tool documentation

**Artifacts**:

- agent: agents/devrun/devrun.md
- doc: docs/devrun/tools/pytest.md, docs/devrun/tools/pyright.md, ...

**Usage**:

- Use Task tool with subagent_type="devrun"
```

## Management Commands

Manual registry management is available via CLI commands:

### `erk kit install <kit-id> --force`

Reinstall a kit and update the registry. Useful if:

- Registry gets out of sync
- Migrating from older erk version
- Recovering from manual edits

```bash
erk kit install <kit-id> --force
```

### `erk kit registry show`

Display the current registry contents:

```bash
erk kit registry show
```

### `erk kit registry validate`

Verify registry matches installed kits:

```bash
erk kit registry validate
```

Checks:

- All installed kits have registry entries
- No orphaned registry entries
- Registry entry files exist and are readable

## Troubleshooting

### Registry out of sync

**Symptom**: Validation fails or registry doesn't match installed kits

**Solution**: Reinstall the affected kit(s)

```bash
erk kit install <kit-id> --force
```

### Missing registry entry

**Symptom**: Kit installed but no registry entry exists

**Solution**: Reinstall the kit

```bash
erk kit install <kit-id> --force
```

### Registry file missing

**Symptom**: `.agent/kits/kit-registry.md` doesn't exist

**Solution**: Install a kit - it will create the registry file

```bash
erk kit install <kit-id>
```

## Design Rationale

### Why separate per-kit files?

- **Kit ownership**: Each kit manages its own documentation entry
- **Independent updates**: Kit updates don't conflict with other kits
- **Clear structure**: Easy to locate and edit individual entries

### Why @-includes instead of direct content?

- **Maintainability**: Registry aggregator stays clean and simple
- **Consistency**: Follows existing CLAUDE.md → AGENTS.md pattern
- **Flexibility**: Easy to add/remove kits by changing one line

### Why minimal pointers (15-20 lines)?

- **Context efficiency**: Prevents context window explosion
- **Discoverability**: Enough info to know what's available
- **On-demand loading**: Agent loads full docs only when needed

## Future Enhancements

Potential improvements for future versions:

- **Version constraints**: Track compatibility between kits
- **Dependency graph**: Show which kits depend on others
- **Usage analytics**: Track which kits are actually being used
- **Schema versioning**: Support evolving registry entry format

## Related Documentation

- [erk-kits GLOSSARY.md](../../../packages/erk-kits/docs/GLOSSARY.md) - Kit terminology
- [AGENTS.md](../../AGENTS.md) - Main agent instructions
- Kit manifest format: See `packages/erk-kits/src/erk_kits/data/kits/*/kit.yaml`
