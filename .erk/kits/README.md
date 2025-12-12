## Purpose

This directory contains the kit registry system for erk-kits, which manages reusable agent components (agents, commands, skills) that extend AI assistant capabilities.

The kit registry provides:

- **Structured catalog** of installed kits and their capabilities
- **Machine-readable format** for AI assistants to discover available functionality
- **Auto-generated documentation** maintained by `erk kit` commands

## For AI Assistants

Load the kit registry to discover what functionality is available in this project:

```markdown
@.erk/kits/kit-registry.md
```

The registry will expand to show all installed kits with references to their individual documentation. Each kit entry provides information about available agents, commands, and skills.

## For Developers

Manage kits using `erk kit` commands:

- `erk kit list` - Show installed kits
- `erk kit install <kit-id>` - Install a kit
- `erk kit sync` - Regenerate registry from installed kits

## Maintenance

The `kit-registry.md` file and individual `registry-entry.md` files are auto-generated. Do not edit them manually - changes will be overwritten by `erk kit sync`.
