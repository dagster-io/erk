# Plan: `/debug-run` Command for GitHub Actions Log Analysis

## Summary

Create a `/debug-run` Claude command that analyzes failed GitHub Actions workflow runs, downloading logs and providing fix recommendations for trivial issues or detailed explanations for complex ones.

## Architecture

**Two-component design:**

1. **Kit CLI command** (`fetch-run-logs`): Handles deterministic work - parsing run references, fetching logs via `gh`, extracting failure metadata
2. **Claude command** (`debug-run.md`): Invokes kit command and performs semantic analysis of failures

## Implementation Steps

### Step 1: Create Kit CLI Command

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/fetch_run_logs.py`

**Functionality**:

- Parse run reference (plain ID like `12345678` or GitHub URL like `https://github.com/owner/repo/actions/runs/12345678`)
- Fetch workflow run metadata via `gh run view <id> --json status,conclusion,headBranch,displayTitle`
- Fetch logs via `gh run view <id> --log`
- Save full logs to `.erk/scratch/run-logs-<run_id>.txt` (creates dir if needed)
- Output structured JSON with run info and path to log file

**Input/Output**:

```bash
dot-agent run erk fetch-run-logs "12345678"
dot-agent run erk fetch-run-logs "https://github.com/owner/repo/actions/runs/12345678"
```

**JSON Output Schema**:

```json
{
  "success": true,
  "run_id": "12345678",
  "run_url": "https://github.com/owner/repo/actions/runs/12345678",
  "workflow_info": {
    "status": "completed",
    "conclusion": "failure",
    "branch": "feature-branch",
    "display_title": "Fix authentication bug"
  },
  "log_file": ".erk/scratch/run-logs-12345678.txt"
}
```

**Error Cases**:

- Invalid reference format → `{"success": false, "error": "invalid_format", "message": "..."}`
- Run not found → `{"success": false, "error": "not_found", "message": "..."}`
- gh CLI issues → `{"success": false, "error": "gh_error", "message": "..."}`
- Run still in progress → `{"success": false, "error": "in_progress", "message": "...", "status": "in_progress"}`

### Step 2: Register in kit.yaml

**File**: `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`

Add entry:

```yaml
- name: fetch-run-logs
  path: kit_cli_commands/erk/fetch_run_logs.py
  description: Fetch GitHub Actions workflow run logs for failure analysis
```

### Step 3: Create Claude Command

**File**: `.claude/commands/debug-run.md`

**Structure**:

```markdown
---
description: Debug a GitHub Actions workflow run and recommend fixes
argument-hint: <run-id-or-url>
---

# /debug-run

[Usage examples]

## Agent Instructions

### Step 1: Fetch Logs

Call: `dot-agent run erk fetch-run-logs "$ARGUMENTS"`

### Step 2: Handle Errors

[Error case handling]

### Step 3: Analyze Failures

[Guidance on identifying failure types and root causes]

### Step 4: Classify Fix Complexity

[Criteria for trivial vs non-trivial]

### Step 5: Output Analysis

[Format for recommendations vs explanations]
```

## Key Design Decisions

1. **URL parsing follows `parse_issue_reference.py` pattern** - Regex for URL, `isdigit()` for plain numbers

2. **Use `gh run view --log` not `--log-failed`** - `--log-failed` only shows failed steps which loses context; full logs provide better analysis material

3. **Save logs to `.erk/scratch/`** - Full logs saved to disk for reference; Claude command reads the file for analysis

4. **Kit command does NO semantic analysis** - Just fetches/formats data; all interpretation done by Claude

5. **Recommend only, no auto-apply** - Per user requirement

## Files to Create/Modify

| File                                                                                            | Action             |
| ----------------------------------------------------------------------------------------------- | ------------------ |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit_cli_commands/erk/fetch_run_logs.py` | Create             |
| `packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml`                               | Modify (add entry) |
| `.claude/commands/debug-run.md`                                                                 | Create             |

## Reference Files

- `parse_issue_reference.py` - Pattern for URL/ID parsing with dataclasses
- `real.py:816-823` - Existing `get_run_logs` implementation using subprocess
- `plan_save_to_issue.py` - Pattern for complex kit CLI command with JSON output
