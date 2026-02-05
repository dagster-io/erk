---
title: Async Learn Local Preprocessing
read_when:
  - working with async learn workflow, debugging trigger-async-learn command, understanding local vs remote session preprocessing
last_audited: "2026-02-05 13:30 PT"
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

Calls `_discover_sessions()` imported from `get_learn_sessions.py`, passing `github_issues`, `claude_installation`, `repo_root`, `cwd`, and `issue_number`. Returns a dict with a `session_sources` list containing local and remote session metadata.

### Step 2: Create Learn Materials Directory

Creates `.erk/scratch/learn-{issue_number}` under the repo root. This directory holds preprocessed sessions and PR comments before uploading to gist.

### Step 3: Preprocess Local Sessions

For each session where `source_type == "local"`, calls `_preprocess_session_direct()` with `max_tokens=20000`. Sessions matching the planning session ID get prefix `"planning"`; all others get `"impl"`. Empty and warmup sessions are filtered out. Output is preprocessed XML file(s) written to the learn directory.

### Step 4: Fetch PR Comments

Looks up the PR associated with the plan issue via `_get_pr_for_plan_direct()`, then fetches two types of comments using direct gateway calls:

- **Review comments** (inline code comments) via `github.get_pr_review_threads()` -- writes to `pr-review-comments.json`
- **Discussion comments** (PR conversation) via `GitHubChecks.issue_comments()` -- writes to `pr-discussion-comments.json`

**Graceful degradation**: If PR doesn't exist, these steps are skipped.

### Step 5: Upload Materials to Gist

Combines all files in the learn directory using `combine_learn_material_files()` from `upload_learn_materials.py`, then uploads as a single secret gist via `github.create_gist()`. See [Gist Materials Interchange](../architecture/gist-materials-interchange.md) for the delimiter-based file packing format.

### Step 6: Trigger GitHub Actions Workflow

Calls `github.trigger_workflow()` with workflow `learn.yml`, passing `issue_number` and `gist_url` as inputs, targeting the `master` ref. Returns a workflow run ID used to construct the workflow URL.

## Local vs Remote Sessions

The preprocessing step (Step 3) only applies to **local sessions** (those with `source_type == "local"`). Remote sessions from gists are already preprocessed, so they are skipped during the local preprocessing loop. See `_preprocess_session_direct()` in `trigger_async_learn.py` for the full preprocessing pipeline.

## Related Documentation

- [Gist Materials Interchange](../architecture/gist-materials-interchange.md) -- Gist file packing format
- [Session Preprocessing](../sessions/preprocessing.md) -- What preprocessing does to session XML
- [Learn Workflow](learn-workflow.md) -- Complete async learn flow
