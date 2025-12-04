---
title: Parallel Session Awareness
read_when:
  - "working with session-specific data"
  - "implementing session-scoped features"
  - "accessing plans, scratch files, or session metadata"
---

# Parallel Session Awareness

When working with session-specific data in Claude Code, it's critical to understand that multiple sessions can run in parallel on the same codebase.

## The Problem

**Anti-pattern**: Using "most recent file by mtime"

When multiple Claude sessions run in parallel:

- Files from different sessions may be interspersed by modification time
- "Most recent file" may belong to a different session than the current one
- This leads to incorrect data lookup and cross-session contamination

**Example failure scenario:**

```python
# WRONG: Assumes most recent = current session
def get_latest_plan(plans_dir: Path) -> Path:
    """Get the most recent plan file."""
    plan_files = list(plans_dir.glob("*.md"))
    return max(plan_files, key=lambda f: f.stat().st_mtime)

# Problem: If Session B creates a plan while Session A is still running,
# Session A will incorrectly see Session B's plan as "latest"
```

## The Solution

**Correct pattern**: Session-scoped lookup

Always use session ID to scope data lookups for session-specific resources:

1. **Session logs**: Parse session logs for session-specific metadata
2. **Plan files**: Look for `slug` field in session log entries
3. **Scratch files**: Store at `.erk/scratch/<session-id>/`
4. **Fallback**: Only use mtime when session scoping is unavailable

## Implementation Patterns

### Pattern 1: Session-Scoped Plan Lookup

Plans created in Plan Mode are logged to session logs with a `slug` field:

```python
import json
from pathlib import Path

def find_plan_for_session(session_id: str, project_dir: Path) -> str | None:
    """Find the plan slug created in a specific session."""
    session_file = project_dir / f"{session_id}.jsonl"

    if not session_file.exists():
        return None

    # Parse session log entries
    with open(session_file, encoding="utf-8") as f:
        for line in f:
            try:
                entry = json.loads(line)

                # Look for Plan Mode entries with slug field
                if entry.get("sessionId") == session_id:
                    slug = entry.get("slug")
                    if slug:
                        return slug
            except json.JSONDecodeError:
                continue

    return None

# Usage
slug = find_plan_for_session(current_session_id, project_dir)
if slug:
    plan_path = Path.home() / ".claude" / "plans" / f"{slug}.md"
```

### Pattern 2: Session-Scoped Scratch Files

Scratch files should always be scoped to session ID:

```python
import os
from pathlib import Path

def get_scratch_dir() -> Path | None:
    """Get scratch directory for current session."""
    session_id = os.environ.get("SESSION_CONTEXT", "").split("session_id=")[-1].strip()

    if not session_id:
        return None

    scratch_dir = Path.cwd() / ".erk" / "scratch" / session_id
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir

# Usage - files are automatically session-scoped
scratch = get_scratch_dir()
if scratch:
    work_file = scratch / "my_work.json"
    work_file.write_text(json.dumps(data))
```

### Pattern 3: Agent Log Correlation

When searching agent logs, always filter by session ID:

```python
def find_agent_data_for_session(
    project_dir: Path,
    session_id: str,
    agent_pattern: str = "agent-*.jsonl"
) -> list[dict]:
    """Find data from agent logs for a specific session."""
    results = []

    for agent_file in project_dir.glob(agent_pattern):
        with open(agent_file, encoding="utf-8") as f:
            for line in f:
                try:
                    entry = json.loads(line)

                    # Only include entries from this session
                    if entry.get("sessionId") == session_id:
                        results.append(entry)
                except json.JSONDecodeError:
                    continue

    return results
```

### Pattern 4: Performance Optimization with cwd_hint

When searching for session data, you often need to find the project directory first. There are two approaches:

**Approach 1: Scan all projects (O(n) - slow)**

Without knowing the working directory, you must scan all project directories:

```python
def find_project_dir_for_session_slow(session_id: str) -> Path | None:
    """Find project directory by scanning all projects.

    Performance: O(n) where n = number of project directories
    Typical time: 378ms - 1.6s with 1,476 project directories
    """
    projects_base = Path.home() / ".claude" / "projects"

    if not projects_base.exists():
        return None

    # Must check every project directory
    for project_dir in projects_base.iterdir():
        if not project_dir.is_dir():
            continue

        # Check if this project contains the session
        for session_file in project_dir.glob("*.jsonl"):
            if session_file.stem == session_id:
                return project_dir

    return None
```

**Approach 2: Direct computation with cwd_hint (O(1) - fast)**

When you know the working directory, compute the project directory name directly:

```python
from pathlib import Path

def encode_path_to_project_folder(path: Path) -> str:
    """Encode filesystem path to Claude project folder name.

    Claude Code uses deterministic encoding:
    - Replace "/" with "-"
    - Replace "." with "-"

    Examples:
        /Users/foo/code/app → -Users-foo-code-app
        /Users/foo/.config → -Users-foo--config (double dash for dot dirs)
    """
    return str(path).replace("/", "-").replace(".", "-")

def find_project_dir_for_session_fast(
    session_id: str,
    cwd_hint: Path | None = None
) -> Path | None:
    """Find project directory using working directory hint.

    Performance: O(1) when cwd_hint provided
    Typical time: ~0.1ms (3,780x - 16,000x faster than scanning)

    Args:
        session_id: Session ID to find
        cwd_hint: Optional working directory to compute project path directly

    Returns:
        Project directory path or None if not found
    """
    # Fast path: compute project directory directly from cwd_hint
    if cwd_hint is not None:
        projects_base = Path.home() / ".claude" / "projects"
        encoded = encode_path_to_project_folder(cwd_hint)
        project_dir = projects_base / encoded

        if project_dir.exists():
            # Verify session exists in this project
            session_file = project_dir / f"{session_id}.jsonl"
            if session_file.exists():
                return project_dir

        return None

    # Slow path: scan all projects (fallback)
    return find_project_dir_for_session_slow(session_id)
```

**When to use cwd_hint:**

- ✅ **CLI commands**: Always pass cwd from environment
- ✅ **Kit commands**: Include `--cwd` parameter with default from `os.getcwd()`
- ✅ **Agent operations**: Current working directory is always known
- ❌ **Historical analysis**: Working directory may be unknown for old sessions
- ❌ **Cross-project searches**: Deliberately searching all projects

**Example: Kit CLI command with cwd_hint**

```python
import os
import click
from pathlib import Path

@click.command()
@click.option(
    "--session-id",
    required=True,
    help="Session ID to find plan for"
)
@click.option(
    "--cwd",
    default=os.getcwd,
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    help="Working directory hint for O(1) lookup (default: current directory)"
)
def find_plan_fast(session_id: str, cwd: Path) -> None:
    """Find plan for session using O(1) lookup."""
    # O(1) lookup using cwd_hint
    project_dir = find_project_dir_for_session_fast(session_id, cwd_hint=cwd)

    if not project_dir:
        click.echo(json.dumps({
            "success": False,
            "error": "Project directory not found"
        }))
        return

    # Now search for plan slug in this specific project
    slug = find_plan_slug_in_project(session_id, project_dir)

    click.echo(json.dumps({
        "success": True,
        "slug": slug,
        "project_dir": str(project_dir)
    }))
```

**Performance comparison:**

| Approach                       | Project Directories | Typical Time | Speed-up       |
| ------------------------------ | ------------------- | ------------ | -------------- |
| Scan all (no hint)             | 100                 | 50ms         | 1x (baseline)  |
| Scan all (no hint)             | 1,476               | 378ms - 1.6s | 1x (baseline)  |
| Direct computation (with hint) | any                 | ~0.1ms       | 500x - 16,000x |

**Key insight**: The cwd_hint pattern transforms session lookup from O(n) scanning to O(1) computation, providing 500-16,000x speedup when working directory is known.

## When Mtime Is Acceptable

Modification time is acceptable ONLY for:

1. **Display purposes**: Showing "recently modified" lists to users
2. **Cleanup operations**: Removing old temporary files
3. **Cache invalidation**: Checking if source files changed
4. **Non-session data**: Files that are truly global to the project

Modification time is NEVER acceptable for:

- Looking up the "current" session's data
- Finding plans, configs, or metadata for active work
- Determining which session created a resource

## Related Context

- **Session log structure**: See [layout.md](layout.md) for JSONL format and `slug` field
- **Scratch storage**: See [scratch-storage.md](../planning/scratch-storage.md) for `.erk/scratch/` patterns
- **Session ID access**: See [layout.md](layout.md#session-id-format) for environment variable extraction

## Examples

### Example: Cross-Session Race Condition

**Scenario**: Two sessions working on the same codebase in parallel

```
Timeline:
10:00 AM - Session A starts, creates plan "add-auth-feature"
10:05 AM - Session B starts, creates plan "fix-bug-123"
10:10 AM - Session A tries to find "its" plan using mtime
          ❌ Gets "fix-bug-123" (Session B's plan) because it's newer
```

**Solution**: Session A should look up its plan by session ID:

```python
# Correct: Session-scoped lookup
my_slug = find_plan_for_session(session_a_id, project_dir)
# Returns: "add-auth-feature" (Session A's actual plan)
```

### Example: Kit CLI Push-Down

Session log parsing should be pushed down to Python CLI commands:

**Before (agent does everything)**:

1. Agent searches for project directory
2. Agent reads and parses JSONL files
3. Agent filters by session ID
4. Agent extracts slug field

**After (pushed to CLI)**:

```bash
# CLI handles all the complexity
dot-agent run erk find-plan-slug --session-id abc123

# Returns: "add-auth-feature"
# Or: {"error": "no_plan_found"}
```

Agent only handles:

- Calling the CLI command
- Interpreting the result
- User-facing error messages

## Testing Parallel Sessions

When testing code that accesses session-specific data:

```python
def test_parallel_sessions_isolated(tmp_path: Path) -> None:
    """Test that parallel sessions don't interfere."""
    # Create two session logs with different plans
    session_a_log = tmp_path / "session-aaa.jsonl"
    session_b_log = tmp_path / "session-bbb.jsonl"

    # Session A creates plan at 10:00
    write_plan_entry(session_a_log, "session-aaa", "plan-alpha", timestamp=1000)

    # Session B creates plan at 10:05 (newer mtime)
    write_plan_entry(session_b_log, "session-bbb", "plan-beta", timestamp=1005)

    # Session A should still find its own plan
    slug = find_plan_for_session("session-aaa", tmp_path)
    assert slug == "plan-alpha"  # Not "plan-beta"!
```

## Summary

- **Always scope by session ID** for session-specific data
- **Never rely on mtime** for current session lookup
- **Parse session logs** for metadata like plan slugs
- **Use scratch directories** with session ID in path
- **Filter agent logs** by session ID before processing
- **Push complexity to CLI** for parsing and lookup operations
