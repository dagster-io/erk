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

**CRITICAL: Before extending Codespace gateway with new methods** → Read [Codespace Gateway](codespace-gateway.md) first. Follow 3-place pattern (ABC, Real, Fake). Add abstract method to ABC, implement in RealCodespace with subprocess, implement in FakeCodespace with test tracking. See Gateway ABC Implementation Checklist for 3-place vs 5-place decision.

**CRITICAL: Before reading from or writing to ~/.erk/codespaces.toml directly** → Read [CodespaceRegistry Gateway](codespace-registry.md) first. Use CodespaceRegistry gateway instead. All codespace configuration should go through this gateway for testability.
