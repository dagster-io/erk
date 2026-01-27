---
title: Session Discovery and Fallback Patterns
read_when:
  - "implementing session analysis workflows"
  - "handling missing session files"
  - "enumerating available sessions"
---

# Session Discovery and Fallback Patterns

How to enumerate sessions and implement fallback strategies for missing sessions.

## Table of Contents

- [Discovery Pattern](#discovery-pattern)
- [Fallback Strategies](#fallback-strategies)
- [Never Fail Entirely](#never-fail-entirely)
- [Session Enumeration Commands](#session-enumeration-commands)

---

## Discovery Pattern

### Core Principle

**Always discover what's available before assuming availability.**

Don't assume session files exist. Enumerate and choose from available sessions.

### Discovery Steps

#### 1. List Available Sessions

```bash
erk exec list-sessions
```

**Returns:** List of session IDs and metadata

#### 2. Filter by Criteria

Filter for sessions related to your workflow:

- **Worktree:** Sessions in specific worktree
- **Date range:** Sessions from recent timeframe
- **Issue:** Sessions associated with issue number

#### 3. Select Best Available

Choose the most relevant session(s) from available list:

- **Most recent:** Latest session in worktree
- **Most relevant:** Session associated with target issue
- **All available:** Process all sessions for comprehensive analysis

#### 4. Proceed with Selection

Use selected session(s), implementing fallback if selection is empty.

---

## Fallback Strategies

### Strategy 1: Use Alternative Session

If planning session unavailable, use implementation session:

```bash
# Ideal: Planning session
PLANNING_SESSION=$(get_session_for_phase "planning")

if [ -z "$PLANNING_SESSION" ]; then
  # Fallback: Implementation session
  IMPL_SESSION=$(get_session_for_phase "implementation")

  if [ -n "$IMPL_SESSION" ]; then
    echo "INFO: Planning session unavailable, using implementation session"
    SESSION_FILE="$IMPL_SESSION"
  fi
fi
```

**Rationale:** Implementation session still contains valuable learnings, even if planning context is missing.

### Strategy 2: Reduce Scope

If specific session unavailable, reduce analysis scope:

```bash
if [ ! -f "$PLANNING_SESSION" ]; then
  echo "INFO: Planning session unavailable, reducing analysis scope"
  echo "INFO: Will analyze implementation session only"

  # Continue with reduced scope
  SESSIONS=("$IMPL_SESSION")
else
  # Full scope
  SESSIONS=("$PLANNING_SESSION" "$IMPL_SESSION")
fi
```

**Rationale:** Partial analysis is better than no analysis.

### Strategy 3: Log and Continue

If session unavailable, log warning but don't fail:

```bash
if [ ! -f "$SESSION_FILE" ]; then
  echo "WARNING: Session ${SESSION_ID} not found"
  echo "INFO: Continuing with available sessions"

  # Don't exit, continue workflow
fi
```

**Rationale:** Workflow should be resilient to missing data.

### Strategy 4: Use Scratch Storage

Check scratch storage before failing:

```bash
SESSION_ID="abc123"

# Check scratch storage first
SCRATCH_FILE=".erk/scratch/sessions/${SESSION_ID}/session.jsonl"

if [ -f "$SCRATCH_FILE" ]; then
  SESSION_FILE="$SCRATCH_FILE"
  echo "INFO: Using session from scratch storage"
elif [ -f ~/.claude/projects/erk/sessions/${SESSION_ID}.jsonl ]; then
  SESSION_FILE=~/.claude/projects/erk/sessions/${SESSION_ID}.jsonl
  echo "INFO: Using session from ~/.claude"
else
  echo "WARNING: Session ${SESSION_ID} not available"
  # Implement fallback
fi
```

**Rationale:** Uploaded sessions persist in scratch storage even if Claude Code session storage is cleared.

---

## Never Fail Entirely

### Core Rule

**Missing session should never cause complete workflow failure.**

### Anti-Pattern: Hard Failure

```bash
# ❌ BAD: Fail hard on missing session
if [ ! -f "$SESSION_FILE" ]; then
  echo "ERROR: Session not found"
  exit 1  # Workflow dies completely
fi
```

**Problems:**

- Workflow blocked
- No progress made
- User must manually intervene
- Wastes agent context

### Correct Pattern: Graceful Degradation

```bash
# ✅ GOOD: Degrade gracefully
if [ ! -f "$SESSION_FILE" ]; then
  echo "INFO: Session ${SESSION_ID} unavailable"
  echo "INFO: Continuing with reduced scope"
  # Continue with available data
fi
```

**Advantages:**

- Workflow continues
- Partial progress made
- User sees results (even if incomplete)
- Can retry later with more data

---

## Session Enumeration Commands

### List All Sessions

```bash
erk exec list-sessions
```

**Output:**

```json
[
  {
    "session_id": "abc123-def456",
    "file_path": "~/.claude/projects/erk/sessions/abc123-def456.jsonl",
    "size_bytes": 157000,
    "modified_at": "2025-01-27T08:20:00Z"
  },
  {
    "session_id": "xyz789-uvw012",
    "file_path": "~/.claude/projects/erk/sessions/xyz789-uvw012.jsonl",
    "size_bytes": 420000,
    "modified_at": "2025-01-26T14:30:00Z"
  }
]
```

### List Sessions for Worktree

```bash
erk exec list-sessions --worktree-name P6172-erk-learn-add-context-pre-01-27-0820
```

**Output:** Sessions associated with specified worktree

### List Sessions by Date Range

```bash
# Sessions from last 7 days
erk exec list-sessions --since "7 days ago"
```

### Get Session Metadata

```bash
erk exec get-session-metadata <session_id>
```

**Output:**

```json
{
  "session_id": "abc123-def456",
  "file_path": "~/.claude/projects/erk/sessions/abc123-def456.jsonl",
  "size_bytes": 157000,
  "modified_at": "2025-01-27T08:20:00Z",
  "associated_issue": 6172,
  "phase": "planning"
}
```

---

## Example: Learn Workflow Fallback

### Scenario

Learn workflow needs planning session for issue #6172, but it may not exist.

### Implementation

```bash
ISSUE_NUMBER=6172

# Try to get planning session
PLANNING_SESSION=$(erk exec get-session-for-issue $ISSUE_NUMBER --phase planning)

if [ -n "$PLANNING_SESSION" ] && [ -f "$PLANNING_SESSION" ]; then
  echo "✓ Found planning session: $PLANNING_SESSION"
  SESSIONS=("$PLANNING_SESSION")
else
  echo "⚠ Planning session unavailable for issue #$ISSUE_NUMBER"

  # Fallback 1: Try implementation session
  IMPL_SESSION=$(erk exec get-session-for-issue $ISSUE_NUMBER --phase implementation)

  if [ -n "$IMPL_SESSION" ] && [ -f "$IMPL_SESSION" ]; then
    echo "✓ Found implementation session: $IMPL_SESSION"
    SESSIONS=("$IMPL_SESSION")
  else
    echo "⚠ No sessions found for issue #$ISSUE_NUMBER"

    # Fallback 2: List all recent sessions in worktree
    WORKTREE_NAME=$(get_current_worktree_name)
    RECENT_SESSIONS=$(erk exec list-sessions --worktree-name "$WORKTREE_NAME" --limit 5)

    if [ -n "$RECENT_SESSIONS" ]; then
      echo "✓ Found recent sessions in worktree: $(echo "$RECENT_SESSIONS" | wc -l) sessions"
      SESSIONS=($(echo "$RECENT_SESSIONS" | jq -r '.[] | .file_path'))
    else
      echo "⚠ No recent sessions available"
      echo "INFO: Skipping session analysis, continuing with other data sources"
      SESSIONS=()
    fi
  fi
fi

# Proceed with whatever sessions we found (or none)
if [ ${#SESSIONS[@]} -gt 0 ]; then
  echo "Analyzing ${#SESSIONS[@]} session(s)..."
  for session in "${SESSIONS[@]}"; do
    analyze_session "$session"
  done
else
  echo "No sessions available, analysis will use other data sources"
fi
```

**Key points:**

1. ✅ Tries planning session first
2. ✅ Falls back to implementation session
3. ✅ Falls back to recent worktree sessions
4. ✅ Logs warnings, doesn't fail
5. ✅ Continues even with zero sessions

---

## Summary: Fallback Hierarchy

| Priority | Source                      | Availability | Quality |
| -------- | --------------------------- | ------------ | ------- |
| 1        | Planning session (target)   | Low          | Highest |
| 2        | Implementation session      | Medium       | High    |
| 3        | Recent worktree sessions    | High         | Medium  |
| 4        | Scratch storage sessions    | Medium       | High    |
| 5        | No sessions (skip analysis) | Always       | N/A     |

**Principle:** Prioritize by quality, but accept lower quality over failure.

---

## Related Documentation

- [Session Lifecycle](lifecycle.md) - Session file persistence and availability patterns
- [Session Preprocessing](preprocessing.md) - Token limits and multi-part file handling
- [Learn Command](../../../.claude/commands/erk/learn.md) - Learn workflow with session discovery
