# Plan: Create `learn-async.yml` CI Workflow

**Part of Objective #4991, Step 3.1**

## Goal

Create a GitHub Actions workflow that enables async learning from implementation sessions. When triggered, the workflow downloads a session artifact, runs the learn command via Claude Code, and creates a PR with documentation updates.

## Context

This is part of the "Enable Remote Session Learning" objective. The async learn workflow is the foundation for non-blocking learning at land time:

1. User lands a PR (step 3.3-3.5 will prompt "Trigger async learn?")
2. If yes: session is uploaded as artifact (step 2.6) + this workflow is dispatched
3. Workflow runs learn command and produces docs PR
4. Land completes immediately without blocking

**Prerequisites (already implemented):**
- `RemoteArtifactSessionSource` (step 2.1) - handles remote sessions
- `erk exec download-remote-session` (step 2.2) - downloads artifacts
- CI uploads session artifacts after impl (step 2.3)
- Plan header tracks artifact location (step 2.4)
- Learn skill handles remote sessions (step 2.5)

**Not yet implemented (will be done in later steps):**
- `erk exec upload-session-artifact` (step 2.6) - for local sessions
- `erk exec trigger-async-learn` (step 3.2) - CLI to dispatch this workflow

## Design Decisions

1. **Workflow inputs**: Accept `issue_number` (required) - the plan issue to learn from
2. **Session handling**: Workflow relies on session artifact already existing (uploaded by erk-impl or step 2.6)
3. **Output**: Create draft PR with documentation changes (allows human review before merge)
4. **Model**: Use haiku for speed/cost since learn is primarily extraction, not complex reasoning
5. **Branch naming**: `learn-{issue_number}-{run_id}` for uniqueness
6. **Update learn_status**: Set to "pending" when workflow starts (step 3.4 will set it before triggering)

## Implementation

### Phase 1: Create `learn-async.yml` workflow

Create `.github/workflows/learn-async.yml` with:

**Triggers:**
```yaml
on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: "Plan issue number to learn from"
        required: true
        type: string
      model_name:
        description: "Claude model to use"
        required: false
        type: string
        default: "claude-haiku-4"
```

**Job steps:**
1. Checkout repo
2. Install uv and erk
3. Configure git (erk-bot identity)
4. Detect trunk branch
5. Create branch: `learn-{issue_number}-{run_id}`
6. Run Claude Code with `/erk:learn {issue_number}`
7. If changes: commit and create draft PR
8. If no changes: post comment on issue noting no learnings

**Key patterns to follow (from existing workflows):**
- Use `ERK_QUEUE_GH_PAT` for checkout (allows pushing)
- Use `CLAUDE_CODE_OAUTH_TOKEN` or `ANTHROPIC_API_KEY` for Claude
- Use `--dangerously-skip-permissions` for non-interactive CI
- Use concurrency group: `learn-async-{issue_number}`

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `.github/workflows/learn-async.yml` | Create | Main async learn workflow |

## Verification

1. **Manual trigger test:**
   ```bash
   gh workflow run learn-async.yml -f issue_number=<plan-issue-with-session>
   ```

2. **Expected behavior:**
   - Workflow runs and downloads session artifact
   - Claude extracts insights and creates docs
   - Draft PR created with documentation updates
   - If no insights: comment posted on issue

3. **Edge cases to verify:**
   - Plan issue with no session artifact → workflow should fail gracefully
   - Plan issue already learned from → workflow should detect and skip/note

## Related Documentation

**Skills to load during implementation:**
- `dignified-python` (if any Python changes needed)
- `fake-driven-testing` (if tests needed)

**Docs to reference:**
- `docs/learned/ci/prompt-patterns.md` - for CI prompt patterns
- `docs/learned/architecture/github-api-rate-limits.md` - REST vs GraphQL