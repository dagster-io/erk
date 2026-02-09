---
title: Gateway Tripwires
read_when:
  - "working on gateway code"
---

<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Edit source frontmatter, then run 'erk docs sync' to regenerate. -->
<!-- Generated from gateway/*.md frontmatter -->

# Gateway Tripwires

Rules triggered by matching actions in code.

**adding -t flag to run_ssh_command or omitting it from exec_ssh_interactive** → Read [Codespace Gateway Pattern](codespace-gateway.md) first. The -t flag controls TTY allocation. Interactive needs it (rendering); non-interactive breaks with it (buffering). See the two execution modes section.

**adding a mutation method to the CodespaceRegistry ABC** → Read [CodespaceRegistry Gateway — Read-Only ABC with Standalone Mutations](codespace-registry.md) first. Mutations are standalone functions in real.py, not ABC methods. This is intentional — see the design rationale below.

**adding dry-run or printing implementation for codespace gateway** → Read [Codespace Gateway Pattern](codespace-gateway.md) first. Codespace operations are all-or-nothing remote execution. Dry-run and printing don't apply.

**implementing codespace gateway** → Read [Codespace Gateway Pattern](codespace-gateway.md) first. Use 3-place pattern (abc, real, fake) without dry-run or print implementations.

**reading from or writing to ~/.erk/codespaces.toml directly** → Read [CodespaceRegistry Gateway — Read-Only ABC with Standalone Mutations](codespace-registry.md) first. Use CodespaceRegistry gateway instead. All codespace configuration should go through this gateway for testability.
