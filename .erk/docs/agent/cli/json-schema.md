---
title: CLI JSON Output Schemas
read_when:
  - "adding --json flag to CLI commands"
  - "parsing JSON output from erk commands"
  - "implementing kit CLI commands with JSON output"
---

# CLI JSON Output Schemas

Conventions and patterns for JSON output in CLI commands.

## General Principles

### Output Mode Flag

Commands with JSON output use `--json` flag:

```python
@click.option("--json", "json_output", is_flag=True, help="Output JSON instead of human-readable text")
def my_command(json_output: bool) -> None:
    if json_output:
        click.echo(json.dumps(result))
    else:
        click.echo(f"Created: {result['name']}")
```

### Error Handling Pattern

JSON commands should output structured errors, not print unstructured messages:

```python
def _error_json(error_type: str, message: str) -> NoReturn:
    """Output error as JSON and exit with code 1."""
    result = {"valid": False, "error_type": error_type, "message": message}
    click.echo(json.dumps(result))
    raise SystemExit(1)
```

### Success/Failure Envelope

Use consistent envelope pattern:

```json
// Success
{"success": true, "data": {...}}

// Failure
{"success": false, "error": "error message", "error_type": "validation_error"}
```

## Kit CLI Command JSON Schemas

Kit CLI commands invoked via `erk kit exec <kit> <command>` produce JSON for agent consumption.

### impl-init

Validates `.impl/` folder and extracts phases.

**Command**: `erk exec impl-init --json`

**Success Output**:

```json
{
  "valid": true,
  "impl_type": "impl", // "impl" or "worker-impl"
  "has_issue_tracking": true,
  "issue_number": 123, // Optional, present if issue.json exists
  "phases": [
    { "number": 1, "text": "Create data model" },
    { "number": 2, "text": "Implement API endpoint" }
  ],
  "related_docs": {
    "skills": ["dignified-python-313", "fake-driven-testing"],
    "docs": ["docs/agent/testing/kit-cli-testing.md"]
  }
}
```

**Error Output**:

```json
{
  "valid": false,
  "error_type": "no_impl_folder",
  "message": "No .impl/ or .worker-impl/ folder found in current directory"
}
```

**Error Types**:

| error_type         | Description                                 |
| ------------------ | ------------------------------------------- |
| `no_impl_folder`   | Neither `.impl/` nor `.worker-impl/` exists |
| `no_plan_file`     | `plan.md` missing from impl folder          |
| `no_progress_file` | `progress.md` missing from impl folder      |

### list-sessions

Lists Claude Code sessions for the current project.

**Command**: `erk exec list-sessions --min-size 1024`

**Output**:

```json
{
  "SESSION_CONTEXT": {
    "current_session_id": "abc123..."
  },
  "project_dir": "/path/to/project/.claude/projects/xyz",
  "branch_context": {
    "branch_name": "feature-123",
    "trunk_branch": "main",
    "is_on_trunk": false
  },
  "sessions": [
    {
      "session_id": "abc123...",
      "file_path": "/path/to/project/.claude/projects/xyz/abc123.jsonl",
      "size_bytes": 45678,
      "modified_time": "2024-01-15T10:30:00",
      "is_current": true
    }
  ]
}
```

### mark-step

Mark implementation steps as complete.

**Command**: `erk exec mark-step 1 2 3`

**Output**:

```json
{
  "success": true,
  "steps_marked": [1, 2, 3],
  "progress": "3/10"
}
```

### check-impl

Validate implementation folder (precursor to impl-init).

**Command**: `erk exec check-impl`

**Output** (same as impl-init but without phases):

```json
{
  "valid": true,
  "impl_type": "impl",
  "has_issue_tracking": true,
  "issue_number": 123
}
```

## Erk CLI JSON Schemas

Main CLI commands with `--json` flag.

### erk wt create

Create a worktree.

**Command**: `erk wt create feature-x --json`

**Output**:

```json
{
  "worktree_name": "feature-x",
  "worktree_path": "/path/to/worktrees/feature-x",
  "branch_name": "feature-x",
  "plan_file": null,
  "status": "created"
}
```

**Status Values**:

| status    | Description              |
| --------- | ------------------------ |
| `created` | New worktree was created |
| `exists`  | Worktree already existed |

### erk plan log

Get plan event history.

**Command**: `erk plan log 123 --json`

**Output**:

```json
{
  "issue_number": 123,
  "events": [
    {
      "event_name": "created",
      "timestamp": "2024-01-15T10:30:00Z",
      "comment_url": null
    },
    {
      "event_name": "impl_started",
      "timestamp": "2024-01-15T11:00:00Z",
      "comment_url": "https://github.com/owner/repo/issues/123#issuecomment-456"
    }
  ]
}
```

## Best Practices

### 1. Always Include Status Field

Include a clear success/valid indicator:

```json
{"valid": true, ...}
{"success": true, ...}
```

### 2. Structured Error Types

Use typed errors for programmatic handling:

```json
{ "error_type": "validation_error", "message": "..." }
```

Not:

```json
{ "error": "Something went wrong" }
```

### 3. Consistent Casing

Use `snake_case` for JSON keys (matches Python conventions):

```json
{ "issue_number": 123, "branch_name": "feature-x" }
```

### 4. Nullable Fields

Use `null` for absent optional data, not empty strings:

```json
{"plan_file": null}  // Good
{"plan_file": ""}    // Bad
```

### 5. Timestamps in ISO 8601

Always use ISO 8601 format for timestamps:

```json
{ "created_at": "2024-01-15T10:30:00Z" }
```

### 6. Exit Codes

- `0`: Success (valid JSON output)
- `1`: Application error (valid JSON with error envelope)
- Non-zero without JSON: System error (e.g., missing command)

## Testing JSON Output

```python
def test_command_json_output(cli_runner, fake_git):
    result = cli_runner.invoke(my_command, ["--json"])
    assert result.exit_code == 0

    output = json.loads(result.output)
    assert output["valid"] is True
    assert "phases" in output
```
