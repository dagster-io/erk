# Documentation Plan: Gist-Based Session Storage

## Background

PR #5403 migrated session storage from GitHub Actions artifacts to GitHub Gists. This enables the `/erk:learn` command to access remote session logs for documentation extraction.

**Why gists over artifacts?**
- Artifacts expire after 30 days; gists persist indefinitely
- Artifacts require authenticated GitHub API access; gists can use simple HTTP fetch
- Gists provide direct raw URLs for downloading

**Architecture change:**
- **Before**: Remote sessions stored as workflow artifacts, downloaded via `gh run download`
- **After**: Remote sessions uploaded to secret gists, downloaded via gist raw URL

## Critical Files to Modify

1. `.claude/commands/erk/learn.md` - **BROKEN** - references removed `--run-id` flag
2. `docs/learned/glossary.md` - Add new plan-header session gist fields

---

## Change 1: Fix `.claude/commands/erk/learn.md`

### Problem

The command currently instructs agents to download remote sessions using artifact-based approach (lines 139-143):

```markdown
- If `source_type == "remote"`: Download the session first, then process:
  1. Run: `erk exec download-remote-session --run-id "<run_id>" --session-id "<session_id>"`
  2. Parse the JSON output to get the `path` field
  3. If `success: true`, use the returned `path` for preprocessing
  4. If `success: false` (artifact expired, permissions error, etc.), inform the user and skip this session
```

The `--run-id` flag **no longer exists**. The command now uses `--gist-url`.

### Changes Required

#### Update 1: session_sources field documentation (lines 41-45)

**Current:**
```markdown
- `session_sources`: List of session source objects, each containing:
  - `source_type`: Either "local" (from ~/.claude) or "remote" (from GitHub Actions)
  - `session_id`: The Claude Code session ID
  - `run_id`: GitHub Actions run ID (for remote sessions only)
  - `path`: File path to the session (for local sessions only)
```

**New:**
```markdown
- `session_sources`: List of session source objects, each containing:
  - `source_type`: Either "local" (from ~/.claude) or "remote" (from GitHub Actions)
  - `session_id`: The Claude Code session ID
  - `run_id`: GitHub Actions run ID (legacy, may be null)
  - `path`: File path to the session (for local sessions only)
  - `gist_url`: Raw gist URL for downloading session (for remote sessions)
```

#### Update 2: Remote session download instructions (lines 139-143)

**Current:**
```markdown
- If `source_type == "remote"`: Download the session first, then process:
  1. Run: `erk exec download-remote-session --run-id "<run_id>" --session-id "<session_id>"`
  2. Parse the JSON output to get the `path` field
  3. If `success: true`, use the returned `path` for preprocessing
  4. If `success: false` (artifact expired, permissions error, etc.), inform the user and skip this session
```

**New:**
```markdown
- If `source_type == "remote"`: Download the session first, then process:
  1. Check if `gist_url` is set (not null). If null, the session cannot be downloaded (legacy artifact-based session).
  2. Run: `erk exec download-remote-session --gist-url "<gist_url>" --session-id "<session_id>"`
  3. Parse the JSON output to get the `path` field
  4. If `success: true`, use the returned `path` for preprocessing
  5. If `success: false` (gist not accessible, etc.), inform the user and skip this session
```

### Related Source Files (for context)

- `src/erk/cli/commands/exec/scripts/download_remote_session.py` - The modified exec script
- `packages/erk-shared/src/erk_shared/learn/extraction/session_source.py` - SessionSource ABC with new `gist_url` property
- `src/erk/cli/commands/exec/scripts/get_learn_sessions.py` - Returns session_sources with gist_url populated

---

## Change 2: Update `docs/learned/glossary.md`

### Location

Add a new subsection under "## Plan & Extraction Concepts" (after line 1068, before "## Abbreviations").

### Content to Add

```markdown
### Session Gist Fields

Plan-header metadata fields for tracking uploaded session logs. Added in PR #5403 to replace artifact-based session storage.

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `last_session_gist_url` | string \| null | URL of the GitHub gist containing the session JSONL file |
| `last_session_gist_id` | string \| null | Gist ID extracted from URL (e.g., "abc123def456") |
| `last_session_id` | string \| null | Claude Code session ID of the uploaded session |
| `last_session_at` | string \| null | ISO 8601 timestamp of when the session was uploaded |
| `last_session_source` | "local" \| "remote" \| null | Where the session originated - "local" for developer machine, "remote" for GitHub Actions |

**Usage:**

These fields are set by:
- `erk exec upload-session` - Uploads session JSONL to gist and updates plan-header
- GitHub Actions workflow (`erk-impl.yml`) - Automatically uploads session after remote implementation

These fields are read by:
- `erk exec get-learn-sessions` - Returns session sources with `gist_url` for download
- `/erk:learn` command - Uses gist URL to download remote sessions for analysis

**Relationship to Legacy Fields:**

The `last_session_*` fields replace the artifact-based approach:
- `last_remote_impl_run_id` - Legacy: GitHub Actions run ID (still populated for backwards compatibility)
- `last_session_gist_url` - New: Direct download URL for session

**Related**: [Learn Plan](#learn-plan), [Plan Header Metadata](architecture/erk-architecture.md)
```

### Related Source Files (for context)

- `packages/erk-shared/src/erk_shared/github/metadata/schemas.py` (lines 412-416) - Field definitions
- `packages/erk-shared/src/erk_shared/github/metadata/plan_header.py` - Functions for updating/extracting these fields
- `packages/erk-shared/src/erk_shared/sessions/discovery.py` - SessionsForPlan dataclass with these fields

---

## Verification

1. **Test learn command with remote session:**
   - Find a plan with `last_session_gist_url` set
   - Run `/erk:learn <issue-number>`
   - Verify remote session downloads successfully

2. **Search for stale references:**
   ```bash
   grep -r "run-id.*session\|artifact.*session" docs/ .claude/commands/ .claude/skills/
   ```

3. **Verify glossary formatting:**
   - Check markdown renders correctly
   - Ensure table alignment is proper

## Files Summary

| File | Action | Lines Affected |
|------|--------|----------------|
| `.claude/commands/erk/learn.md` | Update | ~41-45, ~139-143 |
| `docs/learned/glossary.md` | Add section | After line ~1068 |