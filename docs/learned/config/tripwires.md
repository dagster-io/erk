---
title: Config Tripwires
read_when:
  - "working on config code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from config/*.md frontmatter -->

# Config Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before reading from or writing to ~/.erk/codespaces.toml directly** → Read [Codespaces TOML Configuration](codespaces-toml.md) first. Use CodespaceRegistry gateway instead. All codespace config access should go through the gateway for testability.

**CRITICAL: Before using the field name 'default' in codespaces.toml** → Read [Codespaces TOML Configuration](codespaces-toml.md) first. The actual field name is 'default_codespace', not 'default'. Check RealCodespaceRegistry in real.py for the schema.
