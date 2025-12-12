# dot-agent-kit Development Guide

This package implements the core functionality for Claude Code artifact and kit management.

## Key Documentation

- **[GLOSSARY.md](docs/GLOSSARY.md)**: Definitions of key terms and concepts
  - Artifact types and sources (MANAGED vs LOCAL)
  - Kit structure and configuration
  - Data models (InstalledArtifact, InstalledKit, etc.)
  - Common patterns and CLI command reference

- **[DEVELOPING.md](DEVELOPING.md)**: Development workflow and patterns

- **[HOOKS.md](docs/HOOKS.md)**: Hook development and configuration
  - Creating and modifying hooks
  - Hook architecture and lifecycle
  - Testing and troubleshooting

## Quick Reference

### Important Terminology

Before exploring the codebase or making changes, familiarize yourself with these core concepts (see [GLOSSARY.md](docs/GLOSSARY.md) for full definitions):

- **Artifact**: A Claude Code extension file (skill, command, agent, hook, or doc)
- **Kit**: A packaged collection of related artifacts
- **MANAGED**: Artifact installed from a kit, tracked in `installed.toml`
- **LOCAL**: Artifact created manually, not associated with a kit
- **Level**: USER (`~/.claude/`) or PROJECT (`./.claude/`)

### When to Consult the Glossary

Check [docs/GLOSSARY.md](docs/GLOSSARY.md) when you need to:

- Understand the difference between MANAGED and LOCAL artifacts
- Learn about the data models (InstalledArtifact, ArtifactSource, etc.)
- See examples of common filtering and query patterns
- Understand the structure of `installed.toml`

This prevents the need to explore the codebase just to understand basic terminology.
