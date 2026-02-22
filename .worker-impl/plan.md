# Plan: Add `erk cc usage` for Anthropic Claude Code Analytics

## Context

We want a light CLI command to query the Anthropic Admin API's Claude Code analytics endpoint for per-user daily usage data across multiple Anthropic accounts. The primary use case is visibility into Claude Max subscription users and their consumption. Single command under the existing `erk cc` group.

**API endpoint**: `GET https://api.anthropic.com/v1/organizations/usage_report/claude_code`
- Auth: `x-api-key` header + `anthropic-version: 2023-06-01`
- Params: `starting_at` (YYYY-MM-DD, required), `limit` (max 1000), `page` (cursor)
- Returns per-user daily records with: actor (email/key name), subscription type, sessions, LOC, commits, PRs, model breakdown (tokens + cost), tool actions (accepted/rejected)

## New Files (4 files in `src/erk/cli/commands/cc/usage/`)

### 1. `__init__.py` — Click subgroup

```
erk cc usage --since YYYY-MM-DD [--token TOKEN ...] [--json]
```

### 2. `client.py` — Standalone Anthropic Admin API client

`AnthropicAdminClient`:
- Constructor: `__init__(*, token: str)`
- Headers: `x-api-key` + `anthropic-version: 2023-06-01`
- Single method: `get_claude_code_usage(*, starting_at: str, limit: int) -> list[dict[str, Any]]`
- Auto-pagination via `has_more` / `next_page` cursor
- Custom `AnthropicAdminError` exception

### 3. `shared.py` — Token resolution

`resolve_tokens(tokens: tuple[str, ...]) -> list[str]`:

- If `--token` flags provided: use those (repeatable, 1+)
- Else fall back to env vars: `ANTHROPIC_ADMIN_KEY`, then `ANTHROPIC_API_KEY`
- Else fall back to macOS Keychain: read `"Claude Code-credentials"` service, parse JSON, extract `claudeAiOauth.accessToken`
- Raises `UserFacingCliError` if no tokens resolved

`_read_keychain_token() -> str | None`: shells out to `security find-generic-password -s "Claude Code-credentials" -g`, parses stderr `password:` line, JSON-decodes, returns `accessToken`.

### 4. `usage_cmd.py` — Main command

Options:
- `--token` (multiple=True) — repeatable admin API keys / OAuth tokens
- `--since` (required) — start date YYYY-MM-DD
- `--limit` (default 1000) — max results per page
- `--json` — output raw API response

**Multi-account flow**: For each token, create an `AnthropicAdminClient`, fetch usage data, merge all results into a single list sorted by date/user.

**Table output (expanded per-user breakdown)**:

For each user record:
1. **User summary row** (bold): email/key name, subscription type (highlight Max users), date, sessions, LOC +/-, commits, PRs
2. **Model sub-rows** (indented): model name, input tokens, output tokens, cache tokens, estimated cost
3. **Tool action sub-rows** (indented): tool name, accepted count, rejected count

Max subscription users visually highlighted.

## Modified Files

### `src/erk/cli/commands/cc/__init__.py`

```python
from erk.cli.commands.cc.usage import usage_group
cc_group.add_command(usage_group)
```

## Implementation Order

1. `client.py`
2. `shared.py`
3. `usage_cmd.py`
4. `__init__.py` (usage subgroup)
5. `cc/__init__.py` (register)

## Key Patterns

- Reuse: `UserFacingCliError` from `erk.cli.ensure`
- Reuse: `Console(stderr=True, force_terminal=True)` + Rich `Table` pattern from `cc/session/list_cmd.py`
- No `@click.pass_obj` — self-contained, only needs tokens
- LBYL for optional params

## Verification

1. `erk cc usage --since 2026-02-01` — auto-detect keychain token, show table
2. `erk cc usage --since 2026-02-01 --json` — raw JSON for field name validation
3. `erk cc usage --since 2026-02-01 --token T1 --token T2` — multi-account merged view
4. Verify Max subscription users are highlighted
5. Verify keychain fallback works (unset env vars, no `--token`)

Note: Exact response field names need validation against live API. Use `--json` first, then adjust table mappings.
