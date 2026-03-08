---
title: Erk Dev Tripwires
read_when:
  - "working on erk-dev code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from erk-dev/*.md frontmatter -->

# Erk Dev Tripwires

Rules triggered by matching actions in code.

**adding an exec script that is only called by local slash commands** → Read [Local-Only Scripts Belong in erk-dev](local-only-scripts.md) first. Local-only scripts should live in erk-dev, not erk. The erk package ships to users; erk-dev is developer tooling.

**adding mutation logic to audit-collect** → Read [Audit Collect Command](audit-collect-command.md) first. audit-collect is read-only data collection. It outputs JSON for the /audit-branches command to consume. Never add delete/cleanup operations here.
