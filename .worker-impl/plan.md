# Plan: Seamless Learn on Land

## Overview

Add `--learn` flag to `erk land` that automatically triggers remote learning workflow after landing a PR. Sessions are uploaded to a gist for remote access, and the learning workflow creates a documentation plan issue that can optionally be auto-implemented.

## Architecture

```
erk land --learn [--learn-implement]
    │
    ├─► Validation phase (same as normal land)
    │
    ├─► Session upload phase (NEW)
    │   └─► Preprocess sessions → Upload to secret gist → Store gist URL
    │
    ├─► Execute land (merge PR, cleanup)
    │
    └─► Dispatch learn-extract workflow (NEW)
        │
        └─► Remote: Download from gist → Run /erk:learn → Create docs plan
            │
            └─► If --learn-implement: auto-submit docs plan for implementation
```

## Implementation Steps

### 1. Create `upload-learn-sessions` exec script

**File**: `src/erk/cli/commands/exec/scripts/upload_learn_sessions.py`

```python
# Inputs: --plan-issue, --session-id
# Process:
# 1. find_sessions_for_plan() → get session IDs from GitHub metadata
# 2. get_readable_sessions() → filter to locally available
# 3. For each session: preprocess to XML (reuse preprocess_session logic)
# 4. Upload all files to secret gist via gh gist create
# Output: {"gist_url": "...", "gist_id": "...", "session_count": N}
```

### 2. Create `learn-extract-dispatch.yml` workflow

**File**: `.github/workflows/learn-extract-dispatch.yml`

Inputs:
- `plan_issue_number`: Original plan issue
- `pr_number`: Merged PR number
- `gist_url`: URL of preprocessed sessions gist
- `auto_implement`: Boolean for auto-submitting docs plan

Steps:
1. Checkout repo, install erk/Claude
2. Create branch `learn-extract-{issue}-{timestamp}`
3. Create draft PR for tracking
4. Run: `claude --print /erk:learn {issue} --gist-url {gist_url}`
5. If auto_implement and docs plan created: dispatch `erk-impl.yml`

### 3. Modify `/erk:learn` skill for gist support

**File**: `.claude/commands/erk/learn.md`

Add new argument: `--gist-url <url>`

When provided, replace Step 3 session preprocessing with:
```bash
# Download preprocessed sessions from gist
erk exec download-gist-sessions --gist-url <gist-url> \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn
```

### 4. Create `download-gist-sessions` exec script

**File**: `src/erk/cli/commands/exec/scripts/download_gist_sessions.py`

```python
# Inputs: --gist-url, --output-dir
# Process:
# 1. Extract gist ID from URL
# 2. gh gist view {id} --files → list files
# 3. Download each file to output-dir
# Output: {"files": [...], "count": N}
```

### 5. Create `dispatch-learn-workflow` exec script

**File**: `src/erk/cli/commands/exec/scripts/dispatch_learn_workflow.py`

```python
# Inputs: --plan-issue, --pr-number, --gist-url, --auto-implement
# Process: gh workflow run learn-extract-dispatch.yml -f ...
# Output: {"workflow_url": "..."}
```

### 6. Modify `land_cmd.py`

Add flags:
```python
@click.option("--learn", is_flag=True,
    help="Trigger remote learning workflow after landing")
@click.option("--learn-implement", is_flag=True,
    help="Auto-implement resulting docs plan (implies --learn)")
```

Changes:
- When `--learn` set: skip `_check_learn_status_and_prompt()`
- Before execute: call `upload-learn-sessions`, get gist URL
- In `render_land_execution_script()`: add learn dispatch params
- After execute: dispatch to `learn-extract-dispatch.yml`

### 7. Register exec commands

**File**: `src/erk/cli/commands/exec/group.py`

Add entries for:
- `upload-learn-sessions`
- `download-gist-sessions`
- `dispatch-learn-workflow`

## Critical Files

| File | Purpose |
|------|---------|
| `src/erk/cli/commands/land_cmd.py` | Add --learn flags, integrate upload/dispatch |
| `.claude/commands/erk/learn.md` | Add gist-url argument support |
| `src/erk/cli/commands/exec/scripts/preprocess_session.py` | Reuse preprocessing logic |
| `.github/workflows/learn-dispatch.yml` | Pattern for new workflow |
| `packages/erk-shared/src/erk_shared/sessions/discovery.py` | Session discovery to use |

## Edge Cases

| Case | Handling |
|------|----------|
| No local sessions | Upload returns session_count=0; learn still analyzes PR diff |
| Gist upload fails | Warn, continue land, skip learn dispatch |
| Learn workflow fails | Posts failure comment; land already complete |
| Already learned | Check first; show message, skip dispatch |
| --learn with --dry-run | Show what would dispatch, don't actually upload/dispatch |

## Flag Interactions

| Flags | Behavior |
|-------|----------|
| `--learn` | Upload sessions to gist, dispatch learn workflow after merge |
| `--learn-implement` | Implies --learn; also auto-submits resulting docs plan |
| `--learn -f` | Skips all prompts; triggers learn |
| `--learn --dry-run` | Shows what would happen without executing |

## Verification

1. **Unit tests**: Test session upload, gist download, workflow dispatch (mocked)
2. **Integration test**: Full flow with fake git/github
3. **Manual test**: `erk land --learn` on a real plan with sessions

## Test Commands

```bash
# After implementation, test with:
make fast-ci  # Unit tests pass
erk land --learn --dry-run  # Verify flag parsing
# Then on a real plan branch:
erk land --learn  # Full flow
```