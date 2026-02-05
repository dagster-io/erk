---
title: Async Learn Local Preprocessing
read_when:
  - working with async learn workflow, debugging trigger-async-learn command, understanding local vs remote session preprocessing
last_audited: "2026-02-05 12:55 PT"
audit_result: edited
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

The command orchestrates these steps using **direct Python function calls** (not subprocess invocations):

### Step 1: Discover Session Sources

Calls `_discover_sessions()` directly from `get_learn_sessions.py`:

```python
sessions = _discover_sessions(
    github_issues=github_issues,
    claude_installation=claude_installation,
    repo_root=repo_root,
    cwd=cwd,
    issue_number=issue_number,
)
```

**Output**: Dict with `session_sources` list containing local and remote session metadata.

### Step 2: Create Learn Materials Directory

```python
learn_dir = repo_root / ".erk" / "scratch" / f"learn-{issue_number}"
learn_dir.mkdir(parents=True, exist_ok=True)
```

This directory holds preprocessed sessions and PR comments before uploading to gist.

### Step 3: Preprocess Local Sessions

For each session where `source_type == "local"`, calls `_preprocess_session_direct()`:

```python
output_paths = _preprocess_session_direct(
    session_path=session_path,
    max_tokens=20000,
    output_dir=learn_dir,
    prefix=prefix,  # "planning" or "impl"
)
```

**Prefix logic**:

- `session_id == planning_session_id` → prefix = `"planning"`
- Otherwise → prefix = `"impl"`

**Output**: Preprocessed XML file(s) written to learn directory.

### Step 4: Fetch PR Comments

Uses direct gateway calls (no subprocess):

```python
# Review comments (inline code comments)
threads = github.get_pr_review_threads(repo_root, pr_number, include_resolved=True)
# Writes to: pr-review-comments.json

# Discussion comments (PR conversation)
comments_result = GitHubChecks.issue_comments(github_issues, repo_root, pr_number)
# Writes to: pr-discussion-comments.json
```

**Graceful degradation**: If PR doesn't exist, these steps are skipped.

### Step 5: Upload Materials to Gist

Uses `combine_learn_material_files()` and direct gateway call:

```python
combined_content = combine_learn_material_files(learn_dir)
gist_result = github.create_gist(
    filename=f"learn-materials-plan-{issue_number}.txt",
    content=combined_content,
    description=f"Learn materials for plan #{issue_number}",
    public=False,
)
```

**Format**: Delimiter-based file packing (see [Gist Materials Interchange](../architecture/gist-materials-interchange.md)).

### Step 6: Trigger GitHub Actions Workflow

```python
run_id = github.trigger_workflow(
    repo_root=repo_root,
    workflow=LEARN_WORKFLOW,  # "learn.yml"
    inputs={"issue_number": str(issue_number), "gist_url": str(gist_url)},
    ref="master",
)
```

**Output**: Workflow run ID used to construct workflow URL.

## Local vs Remote Sessions

The preprocessing step only applies to **local sessions**:

```python
for source_item in session_sources:
    if source_item.get("source_type") != "local":
        continue  # Skip remote sessions (already preprocessed)

    # Preprocess local session via direct function call
    output_paths = _preprocess_session_direct(...)
```

**Remote sessions** (from gists) are already preprocessed, so they're not re-processed.

## Related Documentation

- [Gist Materials Interchange](../architecture/gist-materials-interchange.md) — Gist file packing format
- [Session Preprocessing](../sessions/preprocessing.md) — What preprocessing does to session XML
- [Learn Workflow](learn-workflow.md) — Complete async learn flow
