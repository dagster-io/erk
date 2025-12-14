# Audit Findings

## Issue Summary

| Issue                  | Pattern to Fix                              | Files   |
| ---------------------- | ------------------------------------------- | ------- |
| 1. Shell init          | `erk shell-init` → `erk init --shell`       | 2       |
| 2. Config path         | `erk.toml` → `.erk/config.toml`             | 2       |
| 3. Context class       | `DotAgentContext` → `ErkContext`            | 8       |
| 4. Command org         | `erk create` → `erk plan create`            | 1       |
| 5. Protocol/ABC        | Blanket "never Protocol" → nuanced guidance | 1       |
| 6. Path.cwd()          | `Path.cwd()` → `require_cwd(ctx)`           | 9       |
| 7. Kit paths           | `kit_cli_commands/` → `scripts/`            | 10      |
| **Total unique files** |                                             | **~20** |

Note: Some files have multiple issues (e.g., `cli-command-development.md` has issues 3, 6, and 7).

## Verified Patterns

The following grep commands can be used to find remaining issues:

```bash
# DotAgentContext (should be ErkContext)
grep -r "DotAgentContext" .erk/docs/ docs/

# Shell init (should be erk init --shell)
grep -r "erk shell-init" .erk/docs/ docs/

# Config path (should be .erk/config.toml)
grep -r "erk\.toml" .erk/docs/ docs/

# Kit paths (should be scripts/)
grep -r "kit_cli_commands" .erk/docs/ docs/

# Path.cwd() in examples (should be require_cwd(ctx))
grep -r "Path\.cwd()" .erk/docs/ docs/
```
