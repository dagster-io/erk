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

**CRITICAL: Before implementing codespace gateway** → Read [Codespace Gateway Pattern](codespace-gateway.md) first. Use 3-place pattern (abc, real, fake) without dry-run or print implementations.

**CRITICAL: Before reading from or writing to ~/.erk/codespaces.toml directly** → Read [CodespaceRegistry Gateway](codespace-registry.md) first. Use CodespaceRegistry gateway instead. All codespace configuration should go through this gateway for testability.
