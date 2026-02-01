---
read-when: saving plans to GitHub, understanding plan storage locations, working with plan-save-to-issue command, tracking plan state transitions
tripwires: 0
---

# Plan Persistence and Serialization Flow

## Plan State Transitions

Plans transition through three states during their lifecycle:

### 1. In-Memory During Plan Mode

While in Claude Code plan mode, the plan exists only in the agent's working memory. It's being actively developed and refined but not yet persisted.

### 2. Local Markdown in `~/.claude/plans/`

When exiting plan mode, Claude Code saves the plan to a local markdown file:

```
~/.claude/plans/plan-<timestamp>.md
```

This file is:

- Sorted by modification time (most recent first)
- Temporary storage before GitHub persistence
- Available for review and editing before submission

### 3. GitHub Issue via `plan-save-to-issue`

The `erk exec plan-save-to-issue` command converts the local plan to a GitHub issue:

**Input**: Plan markdown file (from `~/.claude/plans/` or explicit path)

**Output**: JSON with issue metadata

```json
{
  "issue_number": 2521,
  "issue_url": "https://github.com/owner/repo/issues/2521",
  "archive_paths": {
    "session_archive": ".erk/scratch/<session-id>/plan.md",
    "timestamped_archive": ".erk/scratch/plans/plan-<timestamp>.md"
  }
}
```

**Side effects**:

- Creates GitHub issue with `erk-plan` label
- Archives plan to `.erk/scratch/` (permanent record)
- Deletes the original `~/.claude/plans/` file (cleanup)

## Session ID in Commands

The `plan-save-to-issue` command references the session via the `--session-id` flag:

```bash
erk exec plan-save-to-issue --session-id "${CLAUDE_SESSION_ID}"
```

### Session ID Availability

**In skills and slash commands**: Use string substitution with `${CLAUDE_SESSION_ID}`

```bash
# Skills can use this substitution directly
erk exec plan-save-to-issue --session-id "${CLAUDE_SESSION_ID}"
```

**In hooks**: Session ID comes from **stdin JSON**, not environment variables. Hooks must interpolate the actual value:

```python
# Hook code receiving session_id from stdin JSON
session_data = json.loads(sys.stdin.read())
session_id = session_data["session_id"]

# Hook interpolates session ID for Claude
print(f"erk exec plan-save-to-issue --session-id {session_id}")
```

## Plan File Cleanup

After successful `plan-save-to-issue`:

1. ✅ Plan content saved to GitHub issue
2. ✅ Plan content archived to `.erk/scratch/`
3. ✅ Original `~/.claude/plans/*.md` file deleted

Deleting the original prevents:

- Confusion about which plan is authoritative
- Accidental re-saves creating duplicate issues
- Stale plans accumulating in the plans directory

## Idempotency

The `plan-save-to-issue` command is idempotent within a session:

1. Checks if a plan issue was already created for this session ID
2. If found, returns the existing issue number instead of creating a duplicate
3. Uses session markers (see [Session-Based Plan Deduplication](session-deduplication.md))

This prevents accidental duplicate issues from command retries.

## Archive Purposes

Plans are archived to `.erk/scratch/` for:

- **Session correlation**: Link plans back to the session that created them
- **Historical analysis**: Learn from previous planning decisions
- **Debugging**: Investigate why a plan was created a certain way
- **Audit trail**: Permanent record even if GitHub issue is deleted

## Related Documentation

- [Plan Lifecycle](lifecycle.md) - Complete plan workflow from creation to merge
- [Session-Based Plan Deduplication](session-deduplication.md) - How idempotency works
- [Scratch Storage](scratch-storage.md) - Archive location and structure
- [Hook Decision Flow](hook-decision-flow.md) - Exit-plan-mode hook options
