---
title: Parallel Session Awareness
read_when:
  - "working with session-specific data"
  - "implementing session-scoped features"
  - "accessing plans, scratch files, or session metadata"
tripwires:
  - action: "working with session-specific data"
    warning: 'Multiple sessions can run in parallel. NEVER use "most recent by mtime" for session data lookup - always scope by session ID.'
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

Plans created in Plan Mode are logged to session logs with a `slug` field. To find a plan for a specific session:

1. Parse the session's JSONL log file
2. Look for entries with `slug` field matching the session ID
3. Return the slug to construct the plan path

**CLI command**: Use `dot-agent run erk find-plan-slug --session-id <id>` for plan lookup.

**Source**: See `session_plan_extractor.py` for the canonical implementation.

### Pattern 2: Session-Scoped Scratch Files

Scratch files should always be scoped to session ID at `.erk/scratch/sessions/<session-id>/`.

Key implementation details:

- Get session ID from `SESSION_CONTEXT` environment variable
- Create directory at `repo_root / ".erk" / "scratch" / "sessions" / session_id`
- Files stored here are automatically session-scoped

**Source**: See `erk_shared/scratch.py` for scratch directory utilities.

### Pattern 3: Agent Log Correlation

When searching agent logs, always filter by session ID:

1. Glob for `agent-*.jsonl` files in the project directory
2. Parse each JSONL file line by line
3. Filter entries where `sessionId` matches the target session
4. Skip malformed JSON entries gracefully

Agent logs use the `agent-<id>.jsonl` naming convention. Only include entries where the `sessionId` field matches your target session.

### Pattern 4: Performance Optimization with cwd_hint

When searching for session data, you often need to find the project directory first. There are two approaches:

**Approach 1: Scan all projects (O(n) - slow)**

Without knowing the working directory, you must scan all project directories under `~/.claude/projects/`. This is O(n) where n = number of project directories. Typical time: 378ms - 1.6s with 1,476 project directories.

**Approach 2: Direct computation with cwd_hint (O(1) - fast)**

When you know the working directory, compute the project directory name directly using Claude Code's deterministic path encoding:

- Replace `/` with `-`
- Replace `.` with `-`
- Example: `/Users/foo/code/app` → `-Users-foo-code-app`

**Source**: See `erk_shared/extraction/session_discovery.py` for `encode_path_to_project_folder()` implementation.

**When to use cwd_hint:**

- ✅ **CLI commands**: Always pass cwd from environment
- ✅ **Kit commands**: Include `--cwd` parameter with default from `os.getcwd()`
- ✅ **Agent operations**: Current working directory is always known
- ❌ **Historical analysis**: Working directory may be unknown for old sessions
- ❌ **Cross-project searches**: Deliberately searching all projects

**CLI command**: Use `dot-agent run erk find-project-dir --cwd <path>` for O(1) project directory lookup.

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
