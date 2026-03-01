---
title: Config Tripwires
read_when:
  - "working on config code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from config/*.md frontmatter -->

# Config Tripwires

Rules triggered by matching actions in code.

**reading from or writing to ~/.erk/codespaces.toml directly** → Read [Codespaces TOML Configuration](codespaces-toml.md) first. Use CodespaceRegistry gateway instead. All codespace config access should go through the gateway for testability.

**setting docs.path at global config level** → Read [External Docs Path Configuration](external-docs-path.md) first. docs_path is REPO_ONLY in RepoConfigSchema. Per-user paths go in .erk/config.local.toml (gitignored).

**using the field name 'default' in codespaces.toml** → Read [Codespaces TOML Configuration](codespaces-toml.md) first. The actual field name is 'default_codespace', not 'default'. Check RealCodespaceRegistry in real.py for the schema.
