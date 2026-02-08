---
title: Gateway Tripwires
read_when:
  - "working on gateway code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from gateway/*.md frontmatter -->

# Gateway Tripwires

Action-triggered rules for this category. Consult BEFORE taking any matching action.

**CRITICAL: Before adding a mutation method to the CodespaceRegistry ABC** → Read [CodespaceRegistry Gateway — Read-Only ABC with Standalone Mutations](codespace-registry.md) first. Mutations are standalone functions in real.py, not ABC methods. This is intentional — see the design rationale below.

**CRITICAL: Before reading from or writing to ~/.erk/codespaces.toml directly** → Read [CodespaceRegistry Gateway — Read-Only ABC with Standalone Mutations](codespace-registry.md) first. Use CodespaceRegistry gateway instead. All codespace configuration should go through this gateway for testability.
