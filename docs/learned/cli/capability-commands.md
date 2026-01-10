---
title: Capability CLI Commands
read_when:
  - "using erk init capability commands"
  - "troubleshooting capability installation"
---

# Capability CLI Commands

## Commands

### `erk init capability list`

Lists all capabilities with scope labels:

```
Available capabilities:
  learned-docs              [project]   Autolearning documentation system
  statusline                [user]      Claude Code status line configuration
```

### `erk init capability add <name>`

Installs capability. Behavior depends on scope:

- **project** capabilities: Require being in a git repository
- **user** capabilities: Work from anywhere

### `erk init capability check [name]`

Without name: Shows all capabilities with status

- Project caps show "?" when outside git repo
- User caps always show installed/not-installed status

With name: Shows detailed status for that capability

- Project caps fail with error if outside git repo
- User caps work from anywhere
