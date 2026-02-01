---
title: Async Learn Local Preprocessing
read_when:
  - working with async learn workflow, debugging trigger-async-learn command, understanding local vs remote session preprocessing
---

# Async Learn Local Preprocessing

The `trigger-async-learn` command orchestrates the full local learn pipeline before triggering the GitHub Actions workflow. This includes preprocessing session XML locally on the developer's machine rather than in the codespace.

## Why Local Preprocessing?

**Previous behavior** (before PR #6460):

- Sessions were uploaded raw (unpreprocessed)
- GitHub Actions codespace preprocessed them during learn execution
- Slow startup time (~30s) for preprocessing in codespace environment

**Current behavior** (after PR #6460):

- Sessions are preprocessed locally before upload
- Preprocessed XML is uploaded to gist
- GitHub Actions codespace uses preprocessed sessions directly
- Faster startup, lower CI resource usage

## 6-Step Orchestration

**File**: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

The command orchestrates these steps:

### Step 1: Get Session Sources

```bash
erk exec get-learn-sessions <issue_number>
```

**Output**: JSON with `session_sources` array containing local and remote session metadata.

**Example**:

```json
{
  "success": true,
  "session_sources": [
    {
      "source": "local",
      "session_path": "/Users/.../.claude/projects/.../sessions/abc123.xml",
      "session_type": "planning"
    },
    {
      "source": "remote",
      "gist_url": "https://gist.github.com/user/xyz789"
    }
  ]
}
```

### Step 2: Create Learn Materials Directory

```python
learn_dir = repo_root / ".erk" / "scratch" / f"learn-{issue_number}"
learn_dir.mkdir(parents=True, exist_ok=True)
```

This directory holds preprocessed sessions and PR comments before uploading to gist.

### Step 3: Preprocess Local Sessions

For each session where `source == "local"`:

```bash
erk exec preprocess-session \
  --input <session_path> \
  --output <learn_dir>/<prefix>-session-<issue_number>.xml
```

**Prefix logic**:

- `session_type == "planning"` → prefix = `"planning"`
- Otherwise → prefix = `"impl"`

**Output**: Preprocessed XML written to learn directory.

### Step 4: Fetch PR Review Comments

```bash
erk exec fetch-learn-pr-comments <issue_number> --output-dir <learn_dir>
```

**Output**: `pr-comments.json` file containing review comments from the PR (if PR exists).

**Graceful degradation**: If PR doesn't exist, the command outputs empty comments file.

### Step 5: Upload Materials to Gist

```bash
erk exec upload-learn-materials <learn_dir> --issue-number <issue_number>
```

**Output**: JSON with `gist_url` pointing to the uploaded materials gist.

**Format**: Delimiter-based file packing (see [Gist Materials Interchange](../architecture/gist-materials-interchange.md)).

### Step 6: Trigger GitHub Actions Workflow

```bash
gh workflow run learn.yml -f issue_number=<issue_number> -f gist_url=<gist_url>
```

**Output**: Workflow run ID and URL.

## \_run_subprocess() Helper Pattern

The command uses a shared helper for subprocess execution with JSON output capture:

```python
def _run_subprocess(cmd: list[str], *, description: str) -> dict[str, object]:
    """Run subprocess, capture stdout JSON, check exit code.

    Args:
        cmd: Command to run (list of strings)
        description: Human-readable description for error messages

    Returns:
        Parsed JSON from stdout

    Raises:
        SystemExit: On subprocess failure (outputs error JSON and exits)
    """
    click.echo(f"[trigger-async-learn] {description}...", err=True)
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode != 0:
        error_msg = f"{description} failed: {result.stderr.strip() or result.stdout.strip()}"
        _output_error(error_msg)

    if not result.stdout.strip():
        _output_error(f"{description} returned empty output")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        _output_error(f"{description} returned invalid JSON: {e}")
```

**Pattern features**:

- Captures both stdout and stderr
- Validates JSON output
- Provides clear error messages with step context
- Exits on failure (no partial execution)

## Dual-Path Branching: Gist URL Present vs Absent

The command handles two scenarios based on whether a gist URL is already present:

### Path 1: Gist URL Already Exists

If `get-learn-sessions` returns a `gist_url` (session already uploaded from previous run):

```python
gist_url = sessions_result.get("gist_url")
if gist_url:
    # Skip preprocessing and upload, use existing gist
    trigger_workflow(issue_number, gist_url)
```

**Use case**: Re-triggering learn for the same session without re-uploading.

### Path 2: No Gist URL (Fresh Learn)

If no `gist_url` in response:

1. Preprocess all local sessions
2. Fetch PR comments
3. Upload materials to new gist
4. Trigger workflow with new gist URL

**Use case**: First-time learn or after session updates.

## Local vs Remote Sessions

The preprocessing step only applies to **local sessions**:

```python
for source_item in session_sources:
    if source.get("source") != "local":
        continue  # Skip remote sessions (already preprocessed)

    # Preprocess local session
    _run_subprocess([
        "erk", "exec", "preprocess-session",
        "--input", session_path,
        "--output", output_path
    ], description=f"Preprocessing {session_type} session")
```

**Remote sessions** (from gists) are already preprocessed, so they're copied directly without re-processing.

## Related Documentation

- [Gist Materials Interchange](../architecture/gist-materials-interchange.md) — Gist file packing format
- [Session Preprocessing](../sessions/preprocessing.md) — What preprocessing does to session XML
- [Learn Workflow](learn-workflow.md) — Complete async learn flow
