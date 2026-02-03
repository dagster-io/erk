---
title: Learn Pipeline Workflow
read_when:
  - "Understanding the complete learn pipeline"
  - "Working with async learn workflow"
  - "Debugging learn plan execution"
  - "Implementing learn plan orchestration"
---

# Learn Pipeline Workflow

## Overview

The learn pipeline extracts insights from implementation sessions and generates documentation. It operates in two modes: **local** (developer-initiated) and **async** (GitHub Actions-triggered).

## Pipeline Stages

### Stage 1: Session Discovery

**Goal**: Find all session logs related to a plan issue.

**Input**: Plan issue number

**Output**: List of session file paths

**Implementation**:

```python
# src/erk/cli/commands/exec/scripts/get_learn_sessions.py
sessions = _discover_sessions(issue_number, repo_root)
# Returns: List of Path objects to session JSONL files
```

**Discovery sources**:

1. **Local sessions** - `~/.claude/projects/<repo>/sessions/*.jsonl`
2. **Gist uploads** - Session files uploaded to GitHub gists (for remote implementation)
3. **Issue comments** - Sessions attached as issue comment gists

### Stage 2: Session Preprocessing

**Goal**: Transform raw session logs into agent-consumable XML format.

**Input**: Session JSONL files

**Output**: Chunked XML files with filtered, deduplicated content

**Processing steps**:

1. **Parse JSONL** - Extract message entries from session log
2. **Filter empty/warmup sessions** - Skip sessions with no meaningful content
3. **Deduplicate documentation blocks** - Remove repeated CLAUDE.md content
4. **Truncate tool parameters** - Shorten large file reads to prevent bloat
5. **Deduplicate assistant messages** - Remove repetitive responses
6. **Discover agent logs** - Find nested agent sessions (`agent-*.jsonl`)
7. **Split to chunks** - Break large sessions into token-limited chunks
8. **Generate XML** - Format as `<session>` XML with metadata

**Implementation**:

```python
# src/erk/cli/commands/exec/scripts/preprocess_session.py
for session_path in sessions:
    chunks = preprocess_session_direct(
        session_path=session_path,
        max_tokens=150000,  # Token limit per chunk
        output_dir=Path("/tmp/learn"),
        prefix="preprocessed"
    )
```

**Output files**:

- `preprocessed-<session_id>.xml` (single chunk)
- `preprocessed-<session_id>-part-01.xml` (multi-chunk)

### Stage 3: PR Review Comment Fetching (Optional)

**Goal**: Collect PR review comments for context.

**Input**: Plan issue number → PR number (via branch lookup)

**Output**: Review comments in markdown format

**Processing**:

```python
# Lenient: PR lookup may fail (plan created before implementation)
pr_info = _get_pr_for_plan_direct(issue_number)
if pr_info:
    comments = fetch_review_comments(pr_info["pr_number"])
else:
    comments = None  # Learn continues without review comments
```

**Why optional**:

- Plan might not have PR yet (just created)
- Implementation might be in progress (no PR created)
- Running from GitHub Actions (no git context for recovery)

### Stage 4: Material Upload to Gist

**Goal**: Bundle all learn materials and upload to GitHub gist for agent access.

**Input**: Preprocessed XML files + review comments

**Output**: Gist URL with all materials

**Bundling**:

```python
# Combine into single learn material file
combined_material = combine_learn_material_files(
    session_files=xml_chunks,
    review_comments=comments,
    issue_number=issue_number
)

# Upload to gist
gist = github.create_gist(
    description=f"Learn materials for issue #{issue_number}",
    files={"learn-materials.md": combined_material}
)
# Returns: Gist URL
```

**Gist contents**:

- Session XML (all chunks concatenated)
- PR review comments (if available)
- Metadata (issue number, timestamp)

### Stage 5: Workflow Trigger

**Goal**: Trigger GitHub Actions workflow to execute learn agent.

**Input**: Gist URL, issue number

**Output**: Workflow run ID and URL

**Trigger**:

```bash
# Trigger learn.yml workflow with gist URL
gh workflow run learn.yml \\
  -f issue_number=<number> \\
  -f gist_url=<url>
```

**Workflow receives**:

- `issue_number` - Plan to update with documentation
- `gist_url` - Pre-processed materials to analyze

### Stage 6: Agent Execution (GitHub Actions)

**Goal**: Analyze sessions and generate documentation.

**Environment**: GitHub Actions workflow (`.github/workflows/learn.yml`)

**Processing**:

1. **Download materials** - Fetch gist content
2. **Launch learn agent** - Claude Code executes `/erk:learn` command
3. **Extract insights** - Agent identifies patterns, decisions, mistakes
4. **Generate docs** - Create markdown files for `docs/learned/`
5. **Create PR** - Submit documentation as pull request

**Agent capabilities**:

- Read session XML to understand implementation context
- Analyze PR review comments for common issues
- Cross-reference with existing docs to avoid duplication
- Generate frontmatter with proper `read_when` triggers

### Stage 7: PR Review and Merge

**Goal**: Human review and merge of generated documentation.

**Workflow**:

1. **Agent creates PR** - With all doc changes
2. **Developer reviews** - Check accuracy, formatting, completeness
3. **Developer merges** - Documentation added to master
4. **Learn plan closes** - Issue marked complete

## Workflow Modes

### Local Learn (Developer-Initiated)

**Command**: `/erk:learn <issue_number>`

**Execution**: Runs all stages locally on developer machine

**Use case**: Quick iteration during development

**Pros**:

- Immediate feedback
- Easy debugging
- Full git context available

**Cons**:

- Requires local Claude Code access
- Uses developer's API quota
- Blocks terminal during execution

### Async Learn (GitHub Actions)

**Command**: `erk exec trigger-async-learn <issue_number>`

**Execution**: Stages 1-5 run locally, stage 6+ run in GitHub Actions

**Use case**: Background processing after landing PR

**Pros**:

- No local blocking
- Parallel execution across multiple plans
- Dedicated API quota (GitHub-managed)

**Cons**:

- Delayed feedback (minutes)
- Requires workflow setup
- No git context (relies on metadata)

## Agent Orchestration

The learn pipeline uses multiple agents:

| Agent                          | Purpose                         | Stage |
| ------------------------------ | ------------------------------- | ----- |
| `session-analyzer`             | Extract patterns from sessions  | 6     |
| `existing-docs-checker`        | Find duplicate/conflicting docs | 6     |
| `documentation-gap-identifier` | Prioritize doc items            | 6     |
| `plan-synthesizer`             | Generate final markdown files   | 6     |

**Parallel execution**: Stages 1-5 prepare materials; stage 6 agents run in parallel where possible.

## Error Handling

### Common Failures

**Stage 1 (Discovery)**:

- No sessions found → Warning, continue with empty list
- Invalid session files → Skip, continue with valid sessions

**Stage 2 (Preprocessing)**:

- Empty sessions → Filter out silently
- Malformed JSONL → Log error, skip file

**Stage 3 (PR Comments)**:

- No PR found → Continue without review comments (lenient)
- API rate limit → Retry with exponential backoff

**Stage 4 (Gist Upload)**:

- API failure → Fail entire pipeline (critical)
- Large content → Chunk or truncate, retry

**Stage 5 (Workflow Trigger)**:

- Workflow not found → Fail with clear error
- Trigger permissions → Check GitHub token scope

**Stage 6 (Agent Execution)**:

- Agent crashes → CI fails, notification sent
- No docs generated → Warning, empty PR created

### Retry Logic

- **PR lookup**: No retry (lenient handler returns None)
- **Gist creation**: 3 retries with exponential backoff
- **Workflow trigger**: 1 retry after 5s delay
- **Agent execution**: No retry (CI job fails)

## Debugging

### Local Debug (Stages 1-5)

```bash
# Run discovery
erk exec get-learn-sessions <issue_number>

# Run preprocessing on single session
erk exec preprocess-session ~/.claude/projects/erk/sessions/<session_id>.jsonl

# Test upload (dry run)
erk exec upload-learn-materials --dry-run <issue_number>

# Full trigger (no dry run)
erk exec trigger-async-learn <issue_number>
```

### GitHub Actions Debug (Stage 6)

```bash
# View workflow run logs
gh run view <run_id>

# Download workflow artifacts
gh run download <run_id>

# Re-run failed workflow
gh run rerun <run_id>
```

## Related Documentation

- [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) - Detailed preprocessing steps
- [Learn Plan Land Flow](../cli/learn-plan-land-flow.md) - Integration with PR landing
- [Frontmatter Tripwire Format](../documentation/frontmatter-tripwire-format.md) - Doc generation format
