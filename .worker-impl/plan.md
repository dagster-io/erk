---
steps:
  - name: "Add plans directory methods to ClaudeInstallation ABC"
  - name: "Migrate local_plans.py and its consumers to use gateway"
  - name: "Migrate find_project_dir.py to use gateway"
---

# Phase 2B: Complete ClaudeInstallation

**Part of Objective #3869, Steps 2B.1-2B.3**

## Goal

Complete the ClaudeInstallation gateway by:
1. Adding plans directory methods to the ABC
2. Migrating `local_plans.py`, `exit_plan_mode_hook.py`, and `find_project_dir.py` to use the gateway
3. Ensuring no production code accesses `~/.claude/` outside ClaudeInstallation

## Current State

The ClaudeInstallation ABC (created in Phase 2A) already has:
- Session operations (has_project, find_sessions, read_session, get_latest_plan, get_session, get_session_path)
- Settings operations (get_settings_path, get_local_settings_path, settings_exists, read_settings)

Key observation: `get_latest_plan()` delegates to `local_plans.get_latest_plan_content()`, which internally uses `Path.home() / ".claude"`. The goal is to move that logic INTO the gateway.

## Implementation

### Step 2B.1: Add plans directory methods to ClaudeInstallation ABC

**Files to modify:**
- `packages/erk-shared/src/erk_shared/extraction/claude_installation/abc.py`
- `packages/erk-shared/src/erk_shared/extraction/claude_installation/real.py`
- `packages/erk-shared/src/erk_shared/extraction/claude_installation/fake.py`

**New abstract methods to add:**

```python
# Plans directory operations
@abstractmethod
def get_plans_dir_path(self) -> Path:
    """Return path to Claude plans directory (~/.claude/plans/)."""
    ...

@abstractmethod
def plans_dir_exists(self) -> bool:
    """Check if plans directory exists."""
    ...

@abstractmethod
def find_plan_by_slug(self, slug: str) -> Path | None:
    """Find a plan file by its slug (filename without .md extension)."""
    ...

@abstractmethod
def list_plan_files(self) -> list[tuple[Path, float]]:
    """List all plan files with their mtimes, sorted newest-first."""
    ...

# Session-to-slug correlation (move from local_plans.py)
@abstractmethod
def extract_slugs_from_session(
    self, session_id: str, cwd_hint: Path | None
) -> list[str]:
    """Extract plan slugs from session log entries."""
    ...

# Projects directory operations (for find_project_dir.py)
@abstractmethod
def get_projects_dir_path(self) -> Path:
    """Return path to Claude projects directory (~/.claude/projects/)."""
    ...

@abstractmethod
def encode_path_to_project_folder(self, path: Path) -> str:
    """Encode filesystem path to Claude project folder name."""
    ...

@abstractmethod
def find_project_info(
    self, path: Path
) -> tuple[Path, list[str], str | None] | None:
    """Find project directory, session logs, and latest session ID for a path.

    Returns:
        (project_dir, session_log_names, latest_session_id) or None if not found
    """
    ...
```

**Implementation approach:**
- `RealClaudeInstallation`: Move logic from `local_plans.py` into the gateway
- `FakeClaudeInstallation`: Extend constructor to accept `plans_dir_data` for testing

### Step 2B.2: Migrate local_plans.py and its consumers

**Files to modify:**
- `packages/erk-shared/src/erk_shared/extraction/local_plans.py` - Thin to re-export from gateway
- `src/erk/cli/commands/exec/scripts/exit_plan_mode_hook.py` - Use gateway instead of direct Path.home()
- `src/erk/cli/commands/exec/scripts/plan_save_to_issue.py` - Use gateway for plans dir
- `packages/erk-shared/src/erk_shared/scratch/plan_snapshots.py` - Use gateway for session/slug lookup

**Consumers found:**
```
real.py:198         → imports get_latest_plan_content (internal, already wired)
exit_plan_mode_hook.py:55 → imports extract_slugs_from_session
plan_save_to_issue.py:41  → imports extract_slugs_from_session, get_plans_dir
plan_snapshots.py:23      → imports extract_slugs_from_session, get_plans_dir, extract_planning_agent_ids
test_local_plans.py:9     → test file (update to test gateway)
```

**Migration for local_plans.py:**
1. Move core logic into RealClaudeInstallation:
   - `_encode_path_to_project_folder()` → `encode_path_to_project_folder()`
   - `_iter_session_entries()` → private method in real.py
   - `find_project_dir_for_session()` → new ABC method
   - `extract_slugs_from_session()` → new ABC method
   - `extract_planning_agent_ids()` → new ABC method
   - `get_plans_dir()` → `get_plans_dir_path()` in ABC
   - `get_latest_plan_content()` → logic moves into existing `get_latest_plan()`
2. Keep `local_plans.py` as thin wrapper for backwards compatibility (deprecated)

**Migration for consumers:**
1. `exit_plan_mode_hook.py`: Use `ClaudeInstallation` from hook context
2. `plan_save_to_issue.py`: Use `ClaudeInstallation` from click context
3. `plan_snapshots.py`: Accept `ClaudeInstallation` as parameter

### Step 2B.3: Migrate find_project_dir.py

**Files to modify:**
- `src/erk/cli/commands/exec/scripts/find_project_dir.py`

**Migration:**
1. Use `ClaudeInstallation.get_projects_dir_path()` instead of `Path.home() / ".claude" / "projects"`
2. Use `ClaudeInstallation.encode_path_to_project_folder()` instead of local function
3. Inject ClaudeInstallation via click context

## Files Summary

| File | Action |
|------|--------|
| `claude_installation/abc.py` | Add ~8 new abstract methods |
| `claude_installation/real.py` | Implement methods, move logic from local_plans.py |
| `claude_installation/fake.py` | Implement methods with in-memory test data |
| `extraction/local_plans.py` | Thin wrapper delegating to gateway (deprecate) |
| `scratch/plan_snapshots.py` | Accept ClaudeInstallation parameter |
| `exec/scripts/exit_plan_mode_hook.py` | Use gateway for ~/.claude/plans/ access |
| `exec/scripts/plan_save_to_issue.py` | Use gateway for plans dir access |
| `exec/scripts/find_project_dir.py` | Use gateway for ~/.claude/projects/ access |
| `tests/unit/extraction/test_local_plans.py` | Update to test gateway methods |

## Testing

- Update existing tests to use `FakeClaudeInstallation` with new constructor parameters
- Ensure tests don't use `monkeypatch` for Path.home()
- Verify: `grep -r "Path.home()" packages/erk-shared/src/` returns only gateway files

## Skills to Load

- `dignified-python` - Required for Python coding standards
- `fake-driven-testing` - Required for test architecture

## Related Documentation

- `docs/learned/architecture/gateway-abc-implementation.md` - 5-file pattern
- `docs/learned/sessions/` - Session discovery patterns