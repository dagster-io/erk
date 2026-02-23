# Restore `--oauth` flag and improve `erk admin gh-actions-api-key` status display

## Context

PR #7768 added an `--oauth` flag to manage `CLAUDE_CODE_OAUTH_TOKEN` alongside `ANTHROPIC_API_KEY`. PR #7790 accidentally reverted it by regenerating admin.py from stale state. The status display also needs improvement to show both GitHub secrets and local env vars in a compact table.

## Files to Modify

1. `src/erk/cli/commands/admin.py` — command implementation
2. `tests/unit/cli/commands/test_admin_gh_actions_api_key.py` — tests

No changes needed to `FakeGitHubAdmin` (already supports arbitrary secret names) or `GitHubAdmin` ABC.

## Implementation

### 1. Add `_SecretConfig` dataclass and resolver (admin.py)

```python
@dataclass(frozen=True)
class _SecretConfig:
    github_secret_name: str
    local_env_var: str
    other_github_secret_name: str

def _resolve_secret_config(*, oauth: bool) -> _SecretConfig:
    if oauth:
        return _SecretConfig(
            github_secret_name="CLAUDE_CODE_OAUTH_TOKEN",
            local_env_var="GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN",
            other_github_secret_name="ANTHROPIC_API_KEY",
        )
    return _SecretConfig(
        github_secret_name="ANTHROPIC_API_KEY",
        local_env_var="GH_ACTIONS_ANTHROPIC_API_KEY",
        other_github_secret_name="CLAUDE_CODE_OAUTH_TOKEN",
    )
```

### 2. Add `--oauth` flag to the Click command

```python
@click.option("--oauth", is_flag=True, help="Target CLAUDE_CODE_OAUTH_TOKEN instead of ANTHROPIC_API_KEY")
```

### 3. Replace status display with compact table

When no action flag, show:

```
GitHub Actions Authentication

  Secret                   GitHub      Local Env
  ANTHROPIC_API_KEY        Set    ←    GH_ACTIONS_ANTHROPIC_API_KEY: Set
  CLAUDE_CODE_OAUTH_TOKEN  Not set     GH_ACTIONS_CLAUDE_CODE_OAUTH_TOKEN: Not set

  Active: ANTHROPIC_API_KEY (takes precedence)
```

Extract helpers:
- `_compute_active_label(*, api_key_exists, oauth_exists) -> str | None` — API key takes precedence
- `_display_secret_row(*, secret_name, github_exists, local_env_var, local_env_value, is_active)` — one table row with ANSI-aware column alignment

### 4. Modify enable/disable to use `_SecretConfig` and auto-switch

- **Enable**: Set target secret (from local env var or prompt), then delete the other secret to prevent ambiguity
- **Disable**: Delete target secret only

### 5. Update and expand tests

**Update existing tests** for new output format:
- `test_status_enabled` → assert "ANTHROPIC_API_KEY" and "Active: ANTHROPIC_API_KEY"
- `test_status_not_found` → assert both "Not set" and guidance message
- `test_status_api_error` → assert "Error"
- `test_enable_sets_secret` → also verify `delete_secret_calls` includes `CLAUDE_CODE_OAUTH_TOKEN`
- `test_disable_deletes_secret` → unchanged (only deletes target)

**Add new tests:**
- `test_status_shows_both_set_with_precedence` — both secrets set, assert "takes precedence"
- `test_status_shows_oauth_only` — only oauth set, assert "Active: CLAUDE_CODE_OAUTH_TOKEN"
- `test_status_shows_local_env_vars` — env vars set, assert "Set" in local column
- `test_enable_oauth_sets_oauth_secret` — `--oauth --enable`, verify correct secret set and API key deleted
- `test_enable_oauth_prompts_when_env_var_not_set` — interactive prompt for oauth token
- `test_disable_oauth_deletes_oauth_secret` — `--oauth --disable`, verify only oauth deleted

## Verification

- Run `uv run pytest tests/unit/cli/commands/test_admin_gh_actions_api_key.py`
- Run `uv run ruff check src/erk/cli/commands/admin.py`
- Run `uv run ty check src/erk/cli/commands/admin.py`
