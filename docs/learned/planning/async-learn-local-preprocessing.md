---
title: Async Learn Local Preprocessing
read_when:
  - working with async learn workflow, debugging trigger-async-learn command, understanding local vs remote session preprocessing
last_audited: 2026-02-05
audit_result: edited
---

# Async Learn Local Preprocessing

The `trigger-async-learn` command orchestrates the full local learn pipeline before triggering the GitHub Actions workflow. All preprocessing happens locally using direct Python function calls rather than subprocess orchestration.

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

## 6-Stage Orchestration

**File**: `src/erk/cli/commands/exec/scripts/trigger_async_learn.py`

The command executes these stages using **direct function calls**, not subprocesses:

### Stage 1: Discover Session Sources

**Implementation**: Direct call to `_discover_sessions()` (line 295)

```python
sessions = _discover_sessions(
    github_issues=github_issues,
    claude_installation=claude_installation,
    repo_root=repo_root,
    cwd=cwd,
    issue_number=issue_number,
)
```

**Output**: Dictionary with `session_sources` array containing session metadata.

**Example session source**:

```json
{
  "success": true,
  "session_sources": [
    {
      "session_id": "abc123",
      "source_type": "local",
      "path": "/Users/.../.claude/projects/.../sessions/abc123.jsonl"
    }
  ],
  "planning_session_id": "abc123"
}
```

### Stage 2: Create Learn Materials Directory

```python
learn_dir = repo_root / ".erk" / "scratch" / f"learn-{issue_number}"
learn_dir.mkdir(parents=True, exist_ok=True)
```

This directory holds preprocessed sessions and PR comments before uploading to gist.

### Stage 3: Preprocess Local Sessions

**Implementation**: Direct call to `_preprocess_session_direct()` (line 369)

For each session where `source_type == "local"`:

```python
output_paths = _preprocess_session_direct(
    session_path=session_path,
    max_tokens=20000,
    output_dir=learn_dir,
    prefix=prefix,
)
```

**Prefix logic** (lines 359-360):

```python
planning_session_id = sessions["planning_session_id"]
prefix = "planning" if session_id == planning_session_id else "impl"
```

**Processing** (lines 108-209):

1. Parse session JSONL
2. Filter empty/warmup sessions (returns `[]` if filtered)
3. Deduplicate documentation blocks
4. Truncate tool parameters
5. Deduplicate assistant messages
6. Discover and process agent logs
7. Split to chunks (20k tokens per chunk)
8. Write XML files with appropriate naming

**Output files**:

- Single chunk: `<prefix>-<session_id>.xml`
- Multi-chunk: `<prefix>-<session_id>-part1.xml`, `part2.xml`, etc.

**Filtering behavior**: If session is empty or warmup, returns empty list and logs skip message (lines 376-379).

### Stage 4: Fetch PR Review and Discussion Comments

**Implementation**: Direct gateway calls (lines 392-472)

**Review comments** (line 413):

```python
threads = github.get_pr_review_threads(repo_root, pr_number, include_resolved=True)
```

**Discussion comments** (line 447):

```python
comments_result = GitHubChecks.issue_comments(github_issues, repo_root, pr_number)
```

**Output files**:

1. `pr-review-comments.json` - Review thread comments from code review
2. `pr-discussion-comments.json` - Discussion comments from PR timeline

**Graceful degradation** (lines 399-404): If PR doesn't exist, skips comment fetching and continues without them.

### Stage 5: Upload Materials to Gist

**Implementation**: Direct gateway calls (lines 474-502)

```python
combined_content = combine_learn_material_files(learn_dir)

gist_result = github.create_gist(
    filename=f"learn-materials-plan-{issue_number}.txt",
    content=combined_content,
    description=f"Learn materials for plan #{issue_number}",
    public=False,
)
```

**Output**: Gist URL pointing to the uploaded materials.

**Format**: Delimiter-based file packing (see [Gist Materials Interchange](../architecture/gist-materials-interchange.md)).

### Stage 6: Trigger GitHub Actions Workflow

**Implementation**: Direct gateway call (lines 511-516)

```python
run_id = github.trigger_workflow(
    repo_root=repo_root,
    workflow=LEARN_WORKFLOW,
    inputs={"issue_number": str(issue_number), "gist_url": str(gist_url)},
    ref="master",
)
```

**Output**: Workflow run ID, used to construct workflow URL.

## Direct Function Call Architecture

The implementation uses **direct Python function calls** rather than subprocess orchestration:

| Stage                  | Function Called                                           | Source                                   |
| ---------------------- | --------------------------------------------------------- | ---------------------------------------- |
| 1. Session discovery   | `_discover_sessions()`                                    | `get_learn_sessions.py:113`              |
| 3. Preprocessing       | `_preprocess_session_direct()`                            | `trigger_async_learn.py:108`             |
| 4. PR lookup           | `_get_pr_for_plan_direct()`                               | `trigger_async_learn.py:212`             |
| 4. Review comments     | `github.get_pr_review_threads()`                          | Gateway method                           |
| 4. Discussion comments | `GitHubChecks.issue_comments()`                           | Gateway method                           |
| 5. Material upload     | `combine_learn_material_files()` + `github.create_gist()` | `upload_learn_materials.py:41` + Gateway |
| 6. Workflow trigger    | `github.trigger_workflow()`                               | Gateway method                           |

**Benefits**:

- No subprocess overhead
- Direct error propagation
- Shared code with CLI commands (e.g., `preprocess_session.py` imports)
- Better testability via dependency injection

## Local vs Remote Sessions

The preprocessing stage only applies to **local sessions**:

```python
for source_item in session_sources:
    if source_item.get("source_type") != "local":
        continue  # Skip remote sessions (already preprocessed)

    # Preprocess local session
    output_paths = _preprocess_session_direct(
        session_path=session_path,
        max_tokens=20000,
        output_dir=learn_dir,
        prefix=prefix,
    )
```

**Remote sessions** (from gists) are already preprocessed, so they're skipped during local preprocessing.

## Diagnostic Output

The command provides rich diagnostic output to stderr (lines 292-502):

**Session discovery** (lines 318-337):

```
📋 Discovering sessions...
   Found 2 session(s): 1 planning, 1 impl
     📝 planning: abc123 (local)
     🔧 impl: def456 (local)
```

**Preprocessing** (lines 362-386):

```
🔄 Preprocessing planning session...
📉 Token reduction: 65.2% (150,000 → 52,100 chars)
   📄 planning-abc123.xml (52,100 chars)
```

**Compression metrics**: Displays original vs compressed sizes with percentage reduction (lines 185-192).

## Related Documentation

- [Gist Materials Interchange](../architecture/gist-materials-interchange.md) — Gist file packing format
- [Session Preprocessing](../sessions/preprocessing.md) — What preprocessing does to session XML
- [Learn Workflow](learn-workflow.md) — Complete async learn flow
