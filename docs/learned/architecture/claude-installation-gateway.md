---
title: ClaudeInstallation Gateway
read_when:
  - "working with Claude Code session logs"
  - "accessing ~/.claude/ directory"
  - "implementing session analysis features"
  - "working with plan files"
tripwires:
  - action: "reading from or writing to ~/.claude/ paths using Path.home() directly"
    warning: "Use ClaudeInstallation gateway instead. All ~/.claude/ filesystem operations should go through this gateway for testability and abstraction."
---

# ClaudeInstallation Gateway

Domain-driven gateway for Claude Code installation operations. Abstracts all filesystem details for `~/.claude/` directory access, making code testable and storage-agnostic.

## Overview

**Location:** `packages/erk-shared/src/erk_shared/gateway/claude_installation/`

**Purpose:** Provides clean interface for accessing Claude Code session logs, settings, and plans without exposing filesystem paths in business logic.

**Key Design:** Storage details are hidden behind the ABC - projects are identified by working directory context, sessions by ID.

## Architecture

The gateway follows the standard 3-file pattern:

- `abc.py` - Abstract interface with domain types
- `real.py` - Production implementation using filesystem
- `fake.py` - In-memory test implementation

## Domain Types

### Session

```python
@dataclass(frozen=True)
class Session:
    session_id: str
    size_bytes: int
    modified_at: float  # Unix timestamp
    is_current: bool
    parent_session_id: str | None  # For agent sessions
```

Domain object for discovered sessions. Unlike `SessionInfo`, this type does NOT expose the filesystem path.

### FoundSession

```python
@dataclass(frozen=True)
class FoundSession:
    session: Session
    path: Path
```

Result of global session lookup - includes the path where the session was found.

### SessionContent

```python
@dataclass(frozen=True)
class SessionContent:
    main_content: str  # Raw JSONL string
    agent_logs: list[tuple[str, str]]  # (agent_id, raw JSONL content)
```

Raw content from a session and its agent logs. Contains raw JSONL strings - preprocessing is done separately.

## Key Methods

### Session Operations

**`has_project(project_cwd: Path) -> bool`**

- Check if a Claude Code project exists for the given working directory

**`find_sessions(project_cwd, *, current_session_id, min_size, limit, include_agents) -> list[Session]`**

- Find sessions for a project, sorted by modified time (newest first)
- Configurable filtering by size and agent inclusion

**`read_session(project_cwd, session_id, *, include_agents) -> SessionContent | None`**

- Read raw session content as JSONL strings
- Optionally include agent subprocess logs

**`get_session(project_cwd, session_id) -> Session | SessionNotFound`**

- Get a specific session by ID
- Returns sentinel object on not found (discriminated union pattern)

**`get_session_path(project_cwd, session_id) -> Path | None`**

- Get the file path for a session
- Returns None if session doesn't exist

**`find_session_globally(session_id) -> FoundSession | SessionNotFound`**

- Find a session by ID across all project directories
- Used when session ID is known but project is not (e.g., from GitHub metadata)

### Settings Operations

**`get_settings_path() -> Path`**

- Return path to global Claude settings file (`~/.claude/settings.json`)

**`get_local_settings_path() -> Path`**

- Return path to local Claude settings file (`~/.claude/settings.local.json`)

**`settings_exists() -> bool`**

- Check if global settings file exists

**`read_settings() -> dict`**

- Read and parse global Claude settings
- Returns empty dict if file doesn't exist or is invalid

**`write_settings(settings: dict) -> Path | None`**

- Write settings to `~/.claude/settings.json` with backup
- Returns path to backup file if created, None if no backup needed

### Plan Operations

**`get_plans_dir_path() -> Path`**

- Return path to `~/.claude/plans/` directory

**`get_latest_plan(project_cwd, *, session_id) -> str | None`**

- Get the latest plan from `~/.claude/plans/`, optionally session-scoped
- Returns plan content as markdown string

**`find_plan_for_session(project_cwd, session_id) -> Path | None`**

- Find plan file path for session using slug lookup
- Searches session logs for slug entries

**`extract_slugs_from_session(project_cwd, session_id) -> list[str]`**

- Extract plan slugs from session log entries
- Slugs indicate plan mode was entered and correspond to plan filenames

**`extract_planning_agent_ids(project_cwd, session_id) -> list[str]`**

- Extract agent IDs for Task invocations with `subagent_type='Plan'`
- Returns agent IDs in format `["agent-<id>", ...]`

### Projects Directory Operations

**`projects_dir_exists() -> bool`**

- Check if `~/.claude/projects/` directory exists

**`get_projects_dir_path() -> Path`**

- Return path to `~/.claude/projects/` directory

## Usage Pattern

**Business logic should NEVER use `Path.home()`** - always use the gateway:

```python
def analyze_session(ctx: ErkContext, session_id: str) -> AnalysisResult:
    # GOOD - uses gateway
    session_content = ctx.claude_installation.read_session(
        ctx.cwd, session_id, include_agents=True
    )

    if session_content is None:
        return AnalysisResult.not_found()

    # Process session_content.main_content and .agent_logs
    ...
```

**Anti-pattern:**

```python
# BAD - bypasses gateway
home = Path.home()
projects_dir = home / ".claude" / "projects"
session_file = projects_dir / hash_directory(cwd) / f"{session_id}.jsonl"
```

## Fake Features

`FakeClaudeInstallation` provides:

- **In-memory session storage** - configurable session data for testing
- **Project directory injection** - tests can create virtual projects
- **Settings management** - in-memory settings without filesystem I/O

## When to Use

Use `ctx.claude_installation` whenever you need to:

- Read session logs (main or agent)
- Access Claude Code settings
- Work with plan files in `~/.claude/plans/`
- Look up project directories
- Find sessions across multiple projects

The gateway ensures:

1. **Testability** - tests use `FakeClaudeInstallation` with controlled data
2. **Abstraction** - business logic doesn't depend on filesystem layout
3. **Storage flexibility** - implementation can change without affecting callers

## Related Topics

- [Session Log Processing](../sessions/raw-session-processing.md) - Processing JSONL content
- [Gateway Inventory](gateway-inventory.md) - All available gateways
- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Handling missing sessions
- [Erk Architecture Patterns](erk-architecture.md) - Gateway dependency injection
