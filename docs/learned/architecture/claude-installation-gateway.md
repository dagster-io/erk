---
title: ClaudeInstallation Gateway
read_when:
  - working with Claude Code session logs
  - accessing ~/.claude/ directory
  - implementing session analysis features
  - working with plan files or settings operations
tripwires:
  - action: "reading from or writing to ~/.claude/ paths using Path.home() directly"
    warning: "Use ClaudeInstallation gateway instead. All ~/.claude/ filesystem operations must go through this gateway for testability and storage abstraction."
    pattern: "Path\\.home\\(\\).*\\.claude"
last_audited: "2026-02-07 19:42 PT"
audit_result: edited
---

# ClaudeInstallation Gateway

## Why This Gateway Exists

Business logic that directly accesses `~/.claude/` via `Path.home()` creates three problems:

1. **Untestable** — Tests must create real directories in the user's home folder or patch `Path.home()` globally
2. **Storage-coupled** — Code assumes filesystem-based storage; switching to remote sessions or in-memory testing requires rewriting call sites
3. **Project-unaware** — The encoded directory name scheme (`-Users-schrockn-code-...`) leaks into every consumer

The ClaudeInstallation gateway solves this by accepting project paths as the lookup key and hiding all encoding/decoding logic behind the interface.

## Domain Abstraction

<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/abc.py, Session/FoundSession/SessionContent types -->

The gateway exposes three domain types that hide filesystem paths:

- **Session** — Discovered session metadata (ID, size, modified time) with no path exposed
- **FoundSession** — Result from global lookup that includes the path where the session was found
- **SessionContent** — Raw JSONL strings from main session + agent logs

See domain type definitions in `packages/erk-shared/src/erk_shared/gateway/claude_installation/abc.py`.

Operations are grouped into three categories: session operations (finding/reading sessions), settings operations (reading/writing Claude settings), and plan operations (slug extraction, plan lookup).

## The Path Encoding Problem

Claude Code stores sessions under `~/.claude/projects/<encoded-path>/` where the encoded path replaces `/` and `.` with `-`. For example, `/Users/schrockn/code/erk` becomes `-Users-schrockn-code-erk`.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/real.py, RealClaudeInstallation._get_project_dir -->

The real implementation handles this encoding scheme and also walks up the directory tree to find parent projects. See `RealClaudeInstallation._get_project_dir()` in `packages/erk-shared/src/erk_shared/gateway/claude_installation/real.py`.

**Why this matters:** If every consumer encodes paths differently, bugs will hide in encoding mismatches. The gateway centralizes this logic.

## Anti-Pattern: Direct Path.home() Access

**WRONG:**

```python
# Business logic coupled to filesystem structure
home = Path.home()
projects_dir = home / ".claude" / "projects"
encoded = str(cwd).replace("/", "-").replace(".", "-")
session_file = projects_dir / encoded / f"{session_id}.jsonl"
content = session_file.read_text()
```

This code is untestable without creating real directories or global mocking, and it duplicates the encoding logic.

**CORRECT:**

<!-- Source: packages/erk-shared/src/erk_shared/context/context.py, ErkContext.claude_installation field -->

```python
# Gateway abstracts storage
session_content = ctx.claude_installation.read_session(
    ctx.cwd, session_id, include_agents=True
)

if session_content is None:
    return AnalysisResult.not_found()

# Process session_content.main_content and .agent_logs
```

The context provides `claude_installation` as a gateway field. See `ErkContext.claude_installation` in `packages/erk-shared/src/erk_shared/context/context.py`.

## Testing Pattern

<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/fake.py, FakeClaudeInstallation.for_test -->

The fake implementation uses `FakeClaudeInstallation.for_test()`, a factory classmethod that accepts declarative test data with all-optional parameters. Tests specify only the data they need (projects with sessions, plans, settings, etc.) and get a fully functional in-memory implementation.

See `FakeClaudeInstallation.for_test()` in `packages/erk-shared/src/erk_shared/gateway/claude_installation/fake.py` for the full parameter list and `FakeProject`/`FakeSessionData` types for the test data structures. This enables fast, deterministic tests without filesystem I/O.

## Project Lookup Behavior

Both real and fake implementations walk up the directory tree to find projects. If you pass `/Users/schrockn/code/erk/worktrees/erk-slot-53`, the gateway checks:

1. `/Users/schrockn/code/erk/worktrees/erk-slot-53` (encoded as `-Users-schrockn-code-erk-worktrees-erk-slot-53`)
2. `/Users/schrockn/code/erk/worktrees` (encoded as `-Users-schrockn-code-erk-worktrees`)
3. `/Users/schrockn/code/erk` (encoded as `-Users-schrockn-code-erk`) ← typically matches here
4. Continues until filesystem root or match found

**Why:** Claude Code projects are created for parent directories, not individual worktrees. All worktrees under the same repository share a single project directory.

<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/real.py, RealClaudeInstallation._get_project_dir -->
<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/fake.py, FakeClaudeInstallation._find_project_for_path -->

See `RealClaudeInstallation._get_project_dir()` and `FakeClaudeInstallation._find_project_for_path()` for the traversal logic.

## Agent Sessions vs Main Sessions

<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/abc.py, Session.parent_session_id field -->

Agent sessions are log files named `agent-<id>.jsonl` that contain subagent execution. They differ from main sessions:

- **Agent sessions** have a `parent_session_id` field linking them to the main session
- **Main sessions** are the top-level conversation logs
- `find_sessions()` accepts `include_agents: bool` to control whether agent sessions appear in results

The `Session` type exposes `parent_session_id: str | None` to distinguish agents from main sessions.

## Global Session Lookup

<!-- Source: packages/erk-shared/src/erk_shared/gateway/claude_installation/abc.py, ClaudeInstallation.find_session_globally -->

When you have a session ID but don't know which project it belongs to (e.g., session IDs stored in GitHub issue metadata), use `find_session_globally()`. It searches all project directories under `~/.claude/projects/` and returns `FoundSession | SessionNotFound` (a discriminated union -- use `isinstance` to branch).

See `ClaudeInstallation.find_session_globally()` in `packages/erk-shared/src/erk_shared/gateway/claude_installation/abc.py` for the full signature and return type.

## Related Topics

- [Gateway Inventory](gateway-inventory.md) — All available gateways
- [Not-Found Sentinel Pattern](not-found-sentinel.md) — Handling missing sessions with `SessionNotFound`
- [Erk Architecture Patterns](erk-architecture.md) — Gateway dependency injection via `ErkContext`
- [Session Log Processing](../sessions/raw-session-processing.md) — Processing the raw JSONL content returned by this gateway
