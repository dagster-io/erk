---
title: Session Discovery Architecture
read_when:
  - "finding Claude Code sessions for a plan"
  - "implementing session lookup from GitHub issues"
  - "understanding dual-source discovery patterns"
  - "working with gist-based session storage"
  - "downloading remote sessions for learn workflow"
tripwires:
  - action: "downloading remote sessions with erk exec download-remote-session --gist-url"
    warning: "Check `last_session_gist_url != null` first. Legacy artifact-based sessions have no gist URL and require different handling (download from workflow artifacts)."
  - action: "preprocessing sessions in erk learn workflow"
    warning: "Inspect `source.source_type` to determine local vs remote access. LocalSessionSource paths point to ~/.claude/projects/, RemoteSessionSource paths point to .erk/scratch/remote-sessions/."
---

# Session Discovery Architecture

Erk discovers Claude Code sessions associated with plans through a unified gist-based approach, with local filesystem fallback for backwards compatibility.

## Core Data Structure

The `SessionsForPlan` dataclass represents all sessions associated with a plan:

- `planning_session_id` - From `created_from_session` field in plan-header metadata
- `implementation_session_ids` - From `impl-started`/`impl-ended` issue comments
- `learn_session_ids` - From `learn-invoked` issue comments
- `last_session_gist_url` - URL of gist containing latest session JSONL
- `last_session_id` - Session ID of latest uploaded session
- `last_session_source` - "local" or "remote" indicating session origin

See `packages/erk-shared/src/erk_shared/sessions/discovery.py` for the canonical implementation.

## Unified Gist-Based Session Storage

Session JSONL files are stored in GitHub Gists, enabling both local and remote sessions to be accessed uniformly. This replaces the previous artifact-based storage for remote sessions.

### Why Gists?

- **Universal access**: Gists can be created from any context (CLI or CI), unlike artifacts which require workflow context
- **Unified handling**: Both local and remote sessions use the same storage mechanism
- **Persistent**: Gists don't expire like workflow artifacts (90-day retention)
- **Direct download**: Raw gist URLs allow direct HTTP fetches without authentication

### Plan Header Fields for Session Gists

The plan-header metadata tracks the latest session:

| Field                   | Description                                |
| ----------------------- | ------------------------------------------ |
| `last_session_gist_url` | URL of gist containing session JSONL       |
| `last_session_gist_id`  | Gist ID for reference                      |
| `last_session_id`       | Claude Code session ID                     |
| `last_session_at`       | ISO 8601 timestamp when session was stored |
| `last_session_source`   | "local" or "remote" indicating origin      |

### Upload Flow

Sessions are uploaded via `erk exec upload-session`:

1. Read session JSONL file
2. Create secret gist with descriptive filename (`session-{id}.jsonl`)
3. Optionally update plan-header metadata with gist info

The CI workflow (`erk-impl.yml`) uploads sessions after implementation:

```bash
erk exec upload-session \
  --session-file "$SESSION_FILE" \
  --session-id "$SESSION_ID" \
  --source remote \
  --issue-number "$ISSUE_NUMBER"
```

### Download Flow

Remote sessions are downloaded via `erk exec download-remote-session`:

1. Fetch session content from gist raw URL
2. Store in `.erk/scratch/remote-sessions/{session_id}/session.jsonl`
3. Return path for learn workflow processing

## Discovery Sources

### Primary: GitHub Issue Metadata

Sessions are tracked in the plan issue through:

1. **Plan header gist fields** - `last_session_gist_url` stores the most recent session gist
2. **Plan header metadata** - `created_from_session` field stores the planning session ID
3. **Implementation comments** - `impl-started` and `impl-ended` comments track implementation sessions
4. **Learn comments** - `learn-invoked` comments track previous learn invocations

This approach makes GitHub the authoritative source, enabling cross-machine session discovery.

### Fallback: Local Filesystem

When GitHub has no tracked sessions (older issues created before session tracking), scan `~/.claude/projects/` for sessions where `gitBranch` matches `P{issue}-*`.

Use `find_local_sessions_for_project()` for this fallback path.

## Key Functions

| Function                            | Purpose                                          |
| ----------------------------------- | ------------------------------------------------ |
| `find_sessions_for_plan()`          | Extract session IDs from GitHub issue metadata   |
| `get_readable_sessions()`           | Filter to sessions that exist on local disk      |
| `find_local_sessions_for_project()` | Scan local sessions by branch pattern (fallback) |
| `extract_implementation_sessions()` | Parse impl session IDs from issue comments       |
| `extract_learn_sessions()`          | Parse learn session IDs from issue comments      |

### Session Source Abstraction

The `SessionSource` ABC provides a uniform interface for session metadata:

| Class                 | Use Case                                       |
| --------------------- | ---------------------------------------------- |
| `LocalSessionSource`  | Sessions from `~/.claude/projects/` on machine |
| `RemoteSessionSource` | Sessions downloaded from gists                 |

Both provide: `source_type`, `session_id`, `run_id` (remote only), and `path`.

## Gateway Methods

The GitHub gateway includes gist operations:

| Method        | Purpose                                   |
| ------------- | ----------------------------------------- |
| `create_gist` | Create a GitHub gist with session content |

Returns `GistCreated` (with `gist_id`, `gist_url`, `raw_url`) or `GistCreateError`.

## Pattern: Dual-Source Discovery

This pattern appears throughout erk when data can come from multiple sources:

1. **Check authoritative source first** (GitHub issue metadata with gist info)
2. **Fallback to local scan** when authoritative source lacks data
3. **Merge results** if both sources provide partial information

This enables:

- Cross-machine workflows (GitHub is authoritative)
- Backwards compatibility (older issues without metadata)
- Offline resilience (local fallback when GitHub unavailable)

## Related Topics

- [Impl Folder Lifecycle](impl-folder-lifecycle.md) - How .impl/ tracks implementation state
- [Markers](markers.md) - How impl-started/ended comments are created
- [Gateway ABC Implementation](gateway-abc-implementation.md) - How create_gist is implemented across gateway layers
