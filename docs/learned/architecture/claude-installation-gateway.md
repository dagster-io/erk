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
last_audited: "2026-02-05"
audit_result: edited
---

# ClaudeInstallation Gateway

Domain-driven gateway for Claude Code installation operations. Abstracts all filesystem details for `~/.claude/` directory access, making code testable and storage-agnostic.

**Location:** `packages/erk-shared/src/erk_shared/gateway/claude_installation/`

Follows the standard 3-file pattern: `abc.py` (abstract interface with domain types), `real.py` (production implementation), `fake.py` (in-memory test implementation).

## Domain Types and Methods

See `abc.py` for all domain types (`Session`, `FoundSession`, `SessionContent`) and method signatures. The gateway provides operations in three categories:

- **Session operations**: `find_sessions()`, `read_session()`, `get_session()`, `find_session_globally()`
- **Settings operations**: `read_settings()`, `write_settings()`, `settings_exists()`
- **Plan operations**: `get_latest_plan()`, `find_plan_for_session()`, `extract_slugs_from_session()`

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

## Related Topics

- [Session Log Processing](../sessions/raw-session-processing.md) - Processing JSONL content
- [Gateway Inventory](gateway-inventory.md) - All available gateways
- [Not-Found Sentinel Pattern](not-found-sentinel.md) - Handling missing sessions
- [Erk Architecture Patterns](erk-architecture.md) - Gateway dependency injection
