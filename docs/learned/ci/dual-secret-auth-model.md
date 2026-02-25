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

The `erk admin gh-actions-api-key` command manages two mutually exclusive authentication secrets for Claude Code in GitHub Actions.

## Authentication Secrets

| GitHub Secret             | Local Env Var                        | Auth Type  | Flag      |
| ------------------------- | ------------------------------------ | ---------- | --------- |
| `ANTHROPIC_API_KEY`       | `GH_ACTIONS_ANTHROPIC_API_KEY`       | Direct API | (default) |
| `CLAUDE_CODE_OAUTH_TOKEN` | `GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN` | OAuth      | `--oauth` |

The two secrets are mutually exclusive: enabling one automatically deletes the other. The local env var provides the value when using `--enable`. If not set, the command prompts interactively.

## Status Display (3-state model per secret)

<!-- Source: src/erk/cli/commands/admin.py, gh_actions_api_key -->

`secret_exists()` is called for both `ANTHROPIC_API_KEY` and `CLAUDE_CODE_OAUTH_TOKEN`, each returning `bool | None`:

- `True` → green "Set"
- `False` → yellow "Not set"
- `None` → red "Error" (API error)

## Command Usage

```bash
erk admin gh-actions-api-key                # Show status of both secrets
erk admin gh-actions-api-key --enable       # Set ANTHROPIC_API_KEY (deletes CLAUDE_CODE_OAUTH_TOKEN)
erk admin gh-actions-api-key --disable      # Delete ANTHROPIC_API_KEY
erk admin gh-actions-api-key --oauth --enable   # Set CLAUDE_CODE_OAUTH_TOKEN (deletes ANTHROPIC_API_KEY)
erk admin gh-actions-api-key --oauth --disable  # Delete CLAUDE_CODE_OAUTH_TOKEN
```

## Error Handling

Both `--enable` and `--disable` raise `UserFacingCliError` on failure, following the standard erk CLI error pattern.

## Code Location

<!-- Source: src/erk/cli/commands/admin.py -->

`src/erk/cli/commands/admin.py` — `gh_actions_api_key()`: command definition with inline status display, enable, and disable logic.
