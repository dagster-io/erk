---
title: Session File Lifecycle and Persistence
read_when:
  - "working with Claude Code sessions"
  - "implementing learn workflows"
  - "accessing planning session files"
tripwires:
  - action: "accessing planning session in learn workflow"
    warning: "Session files are session-scoped, not persistent across Claude Code sessions. If planning session is unavailable, implement fallback strategy using available sessions."
---

# Session File Lifecycle and Persistence

Critical understanding of session file persistence and availability patterns.

## Table of Contents

- [Core Principle: Session-Scoped Persistence](#core-principle-session-scoped-persistence)
- [Session File Locations](#session-file-locations)
- [When Session Files Exist](#when-session-files-exist)
- [When Session Files Are Missing](#when-session-files-are-missing)
- [Fallback Patterns](#fallback-patterns)
- [Session Preprocessing Behavior](#session-preprocessing-behavior)
- [Learn Workflow Implications](#learn-workflow-implications)

---

## Core Principle: Session-Scoped Persistence

**Session files persist only within the current Claude Code session.**

- **Lifetime:** From session start to session end
- **Scope:** Single Claude Code conversation
- **Storage:** `~/.claude/projects/<project>/sessions/<session_id>.jsonl`

**Critical implication:** Session files are **not guaranteed** to exist across different Claude Code sessions.

---

## Session File Locations

### Standard Session Files

```
~/.claude/projects/<project>/sessions/
├── <session_id_1>.jsonl
├── <session_id_2>.jsonl
├── <session_id_3>.part1.jsonl   # Multi-part session
├── <session_id_3>.part2.jsonl
└── <session_id_4>.jsonl
```

### Session Scratch Storage

When sessions are uploaded via `erk exec upload-session`:

```
.erk/scratch/sessions/
├── <session_id>/
│   ├── session.jsonl           # Original session file
│   ├── metadata.json           # Session metadata
│   └── associated_issues.json  # Linked GitHub issues
```

Session scratch storage persists across Claude Code sessions because it's stored in the repository.

---

## When Session Files Exist

### Current Session

The **current** session file always exists:

```bash
# Current session ID available via environment
CLAUDE_SESSION_ID="abc123..."

# File exists
ls ~/.claude/projects/erk/sessions/${CLAUDE_SESSION_ID}.jsonl
```

### Recently Active Sessions

Sessions from **recent** Claude Code interactions (within current project context):

- Sessions from the last few hours/days
- Sessions in the same worktree
- Sessions for the same plan or feature

### Uploaded Sessions

Sessions explicitly uploaded to `.erk/scratch/sessions/` persist across sessions:

```bash
# Upload current session
erk exec upload-session \
  --session-file ~/.claude/projects/erk/sessions/${CLAUDE_SESSION_ID}.jsonl \
  --session-id ${CLAUDE_SESSION_ID} \
  --source local \
  --issue-number 123
```

After upload, session is accessible via `.erk/scratch/sessions/<id>/session.jsonl`.

---

## When Session Files Are Missing

### Different Claude Code Session

If you're in a **different** Claude Code session from when planning occurred:

- Planning session file may not exist in `~/.claude/projects/erk/sessions/`
- Only the current session and recent sessions are available
- Historical sessions are not guaranteed to persist

### Example Scenario

1. **Monday 10am:** User creates plan (session `abc123`)
2. **Monday 11am:** Plan saved to GitHub issue #6172
3. **Tuesday 2pm:** User starts new Claude Code session (session `def456`)
4. **Tuesday 2:15pm:** `/erk:learn 6172` command runs
5. **Result:** Session `abc123` file may not exist in filesystem

### Why This Happens

Claude Code manages session storage lifecycle:

- Sessions are not infinite-retention
- Old sessions may be cleaned up
- Sessions may be moved or archived

**Erk cannot control Claude Code's session storage policy.**

---

## Fallback Patterns

### Pattern 1: Check Before Access

Always verify session file exists before attempting to read:

```bash
SESSION_ID="abc123"
SESSION_FILE=~/.claude/projects/erk/sessions/${SESSION_ID}.jsonl

if [ ! -f "$SESSION_FILE" ]; then
  echo "Warning: Planning session ${SESSION_ID} not found"
  # Implement fallback
fi
```

### Pattern 2: Use Available Sessions

If planning session is unavailable, use other available sessions:

```bash
# List all available sessions
erk exec list-sessions

# Use implementation session instead of planning session
# Or use most recent session related to the issue
```

### Pattern 3: Graceful Degradation

Log warning but continue workflow:

```bash
if [ ! -f "$PLANNING_SESSION" ]; then
  echo "INFO: Planning session unavailable, using implementation session"
  SESSION_FILE="$IMPLEMENTATION_SESSION"
fi
```

### Pattern 4: Check Scratch Storage

Check if session was uploaded to persistent storage:

```bash
SESSION_ID="abc123"

# Check scratch storage first
if [ -f ".erk/scratch/sessions/${SESSION_ID}/session.jsonl" ]; then
  SESSION_FILE=".erk/scratch/sessions/${SESSION_ID}/session.jsonl"
else
  # Fall back to ~/.claude/ location
  SESSION_FILE=~/.claude/projects/erk/sessions/${SESSION_ID}.jsonl
fi

if [ ! -f "$SESSION_FILE" ]; then
  echo "Session ${SESSION_ID} not available"
  # Implement fallback
fi
```

### Pattern 5: Never Fail Entirely

**Critical:** Missing session should never cause complete workflow failure.

```bash
# ANTI-PATTERN: Fail hard on missing session
if [ ! -f "$SESSION_FILE" ]; then
  echo "ERROR: Session not found"
  exit 1  # ❌ Workflow dies
fi

# CORRECT PATTERN: Reduce scope but continue
if [ ! -f "$SESSION_FILE" ]; then
  echo "INFO: Planning session unavailable, reducing analysis scope"
  # Continue with available data
fi
```

---

## Session Preprocessing Behavior

### Single-File Sessions

Sessions under 20K tokens remain as single files:

```
<session_id>.jsonl
```

### Multi-Part Sessions

Sessions over 20K tokens are split:

```
<session_id>.part1.jsonl   # First 20K tokens
<session_id>.part2.jsonl   # Next 20K tokens
<session_id>.part3.jsonl   # Remaining tokens
```

### Downstream Handling

When reading sessions, check for multi-part pattern:

```bash
SESSION_ID="abc123"
BASE_FILE=~/.claude/projects/erk/sessions/${SESSION_ID}.jsonl

if [ -f "${BASE_FILE}" ]; then
  # Single-file session
  SESSION_FILES="${BASE_FILE}"
elif [ -f "${BASE_FILE%.jsonl}.part1.jsonl" ]; then
  # Multi-part session
  SESSION_FILES="${BASE_FILE%.jsonl}.part*.jsonl"
else
  echo "Session ${SESSION_ID} not found"
fi
```

### Token Compression

Session preprocessing achieves 71-92% compression ratio:

- **Raw conversation:** 100K tokens
- **After preprocessing:** 25K-30K tokens
- **Split into:** 2 parts (part1.jsonl, part2.jsonl)

**Implication:** Large sessions may be split even after compression.

---

## Learn Workflow Implications

### Planning Session Access

Learn workflows (`/erk:learn`, `/local:replan-learn-plans`) ideally access:

1. **Planning session** - Where the plan was created
2. **Implementation session** - Where the code was written

But planning session may not be available.

### Handling Missing Planning Sessions

If planning session is unavailable:

#### Option 1: Use Implementation Session Only

```bash
# Implementation session is more likely to be recent/available
IMPL_SESSION=$(erk exec get-implementation-session <issue_number>)

if [ -n "$IMPL_SESSION" ]; then
  # Proceed with implementation session only
  erk learn analyze --session-id "$IMPL_SESSION" ...
fi
```

#### Option 2: Enumerate Available Sessions

```bash
# Get all sessions in worktree
AVAILABLE_SESSIONS=$(erk exec list-sessions --format json)

# Filter for sessions related to the issue
# Use the most recent or most relevant session
```

#### Option 3: Skip Planning Analysis

```bash
if [ ! -f "$PLANNING_SESSION" ]; then
  echo "INFO: Skipping planning analysis (session unavailable)"
  echo "INFO: Proceeding with implementation analysis only"
  # Continue with reduced scope
fi
```

### Discovery Pattern

Always enumerate sessions before assuming availability:

```bash
# Discover what's available
erk exec list-sessions --worktree-name <name>

# Choose best available session(s)
# Proceed with available data
```

---

## Related Documentation

- [Session Discovery and Fallback](discovery-fallback.md) - Session enumeration and fallback strategies
- [Session Preprocessing](preprocessing.md) - Token limits and multi-part file handling
- [Plan Lifecycle](../planning/lifecycle.md) - Plan storage and session references
