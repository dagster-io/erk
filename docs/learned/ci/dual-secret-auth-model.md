---
title: GitHub Actions API Key Management
read_when:
  - "configuring GitHub Actions authentication for Claude Code"
  - "using erk admin gh-actions-api-key"
  - "debugging authentication failures in CI"
tripwires:
  - action: "referencing _enable_secret(), _disable_secret(), or _display_auth_status() functions"
    warning: "These private functions do not exist. The logic is inline within gh_actions_api_key() in src/erk/cli/commands/admin.py."
---

# GitHub Actions API Key Management

The `erk admin gh-actions-api-key` command manages the `ANTHROPIC_API_KEY` secret for Claude Code in GitHub Actions.

## Authentication Secret

| GitHub Secret       | Local Env Var                  | Auth Type  |
| ------------------- | ------------------------------ | ---------- |
| `ANTHROPIC_API_KEY` | `GH_ACTIONS_ANTHROPIC_API_KEY` | Direct API |

The local env var (`GH_ACTIONS_ANTHROPIC_API_KEY`) provides the value when using `--enable`. If not set, the command prompts interactively.

## Status Display (3-state model)

<!-- Source: src/erk/cli/commands/admin.py, gh_actions_api_key -->

`secret_exists()` returns `bool | None`:

- `True` → green "Enabled"
- `False` → yellow "Not found"
- `None` → red "Error checking secret" (API error)

## Command Usage

```bash
erk admin gh-actions-api-key              # Show secret status
erk admin gh-actions-api-key --enable     # Set ANTHROPIC_API_KEY from env var or prompt
erk admin gh-actions-api-key --disable    # Delete ANTHROPIC_API_KEY
```

## Error Handling

Both `--enable` and `--disable` raise `UserFacingCliError` on failure, following the standard erk CLI error pattern.

## Code Location

<!-- Source: src/erk/cli/commands/admin.py -->

`src/erk/cli/commands/admin.py` — `gh_actions_api_key()` (lines 137-194): command definition with inline status display, enable, and disable logic.
