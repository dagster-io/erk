# Claude Code Session Commands

User-facing CLI commands for working with Claude Code sessions.

## Related Documentation

**Before modifying this code, read the session documentation:**

@docs/learned/sessions/

## Architecture

These commands use the `ClaudeCodeSessionStore` abstraction from `erk_shared.extraction.claude_code_session_store`:

- **ABC**: `ClaudeCodeSessionStore` - interface for session operations
- **Real**: `RealClaudeCodeSessionStore` - reads from `~/.claude/projects/`
- **Fake**: `FakeClaudeCodeSessionStore` - in-memory for testing

## Commands

### `erk cc session list`

Lists sessions for the current worktree with session ID, time, size, and summary.

**Key behaviors:**

- By default, excludes agent sessions (files starting with `agent-`)
- `--include-agents` flag includes agent sessions with parent linkage
- Sessions sorted by modification time (newest first)
- Summary extracted from first user message
