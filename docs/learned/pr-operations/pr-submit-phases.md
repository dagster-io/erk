---
title: PR Submit Workflow Phases
read_when:
  - "understanding the erk pr submit workflow"
  - "debugging PR submission issues"
  - "working with AI-generated PR descriptions"
  - "understanding plan context integration in PRs"
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# PR Submit Workflow Phases

The `erk pr submit` command uses a 5-phase workflow to submit PRs with AI-generated descriptions. This document explains each phase and the two-layer architecture.

## Two-Layer Architecture

The workflow has two layers:

1. **Core layer (always runs)**: `git push` + `gh pr create` - works without Graphite
2. **Graphite layer (optional)**: `gt submit` for stack metadata - runs when Graphite is available and branch is tracked

## Workflow Phases

| Phase | Name                          | Description                                   |
| ----- | ----------------------------- | --------------------------------------------- |
| 1     | Creating or Updating PR       | Push changes and create/find PR               |
| 2     | Getting diff and plan context | Extract diff and fetch plan concurrently      |
| 3     | Generating PR description     | AI generates title and body via Anthropic API |
| 4     | Graphite enhancement          | Add stack metadata (if available)             |
| 5     | Updating PR metadata          | Push AI-generated title/body to GitHub        |

### Phase 1: Creating or Updating PR

Two execution paths depending on Graphite availability:

**Standard flow** (Graphite not available or branch not tracked):

- Runs `git push` to push the branch
- Runs `gh pr create` to create PR (or finds existing)
- Returns PR number and base branch

**Graphite-first flow** (Graphite authenticated and branch tracked):

- Runs `gt submit` which handles push + PR creation
- Avoids "tracking divergence" issue
- Queries GitHub API to get PR info after submit

### Phase 2: Getting diff and plan context

Diff extraction and plan context fetching run **concurrently** using `ThreadPoolExecutor(max_workers=2)` (PR #8799). Both involve independent GitHub API calls:

**Diff extraction:**

- Uses GitHub API to get PR diff
- Saves diff to session scratch directory for AI processing
- Includes all commits since parent branch

**Plan context fetching:**
The `PlanContextProvider` checks for a linked erk plan:

1. Looks for `.erk/impl-context/plan-ref.json` (or legacy `.impl/issue.json`) in repo root
2. Extracts issue number from metadata
3. Fetches plan body from GitHub
4. Includes objective summary if linked

**Output**: Both results are merged into pipeline state and passed to the AI generator in Phase 3.

### Phase 3: Generating PR description

- Uses `CommitMessageGenerator` with `LlmCaller` (direct Anthropic API)
- Inputs: diff file, commit messages, branch info, **plan context**
- Outputs: AI-generated title and body

The plan context from Phase 2 helps the AI:

- Match PR description to original intent
- Include relevant context from the plan
- Reference objective if applicable

### Phase 4: Graphite enhancement

Only runs in standard flow (skipped if Graphite-first flow was used):

- Checks if Graphite is available and authenticated
- Runs `gt submit` to add stack metadata
- Generates Graphite stack URL

This phase is non-fatal - errors are warnings, not failures.

### Phase 5: Updating PR metadata

- Updates PR title and body via GitHub API
- Uses AI-generated content from Phase 3
- Embeds plan in PR body via `_build_plan_details_section()` when `plan_context` is present
- Builds checkout footer with metadata section
- Separates commit message (`pr_body`) from GitHub PR body (`pr_body_for_github`)
- Links to Graphite if available

**Plan Embedding**: When `state.plan_context` is available, the phase embeds the full plan content in a collapsible `<details>` section in the PR body. The plan appears on GitHub but **not** in the git commit message. See [Plan Embedding in PR](plan-embedding-in-pr.md) for details.

**Two-Target Pattern**: Phase 5 uses separate strings for commit messages (plain text) and GitHub PR bodies (with HTML enhancements). See [PR Body Formatting](../architecture/pr-body-formatting.md) for the pattern.

## CLI Options

```bash
# Standard submission
erk pr submit

# Skip Graphite enhancement (use git + gh only)
erk pr submit --no-graphite

# Force push (when branch has diverged from remote)
erk pr submit -f

# Show diagnostic output
erk pr submit --debug
```

## Architecture Note

The internal implementation was refactored in PR #6300 from a monolithic function to a linear function pipeline. The 5 user-facing phases described above map to 10 internal pipeline steps in `submit_pipeline.py`. See [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) for the internal step-by-step architecture.

## Related Topics

- [PR Submit Pipeline Architecture](../cli/pr-submit-pipeline.md) - Internal pipeline implementation
- [Commit Message Generation](commit-message-generation.md) - AI generation details
- [Plan Lifecycle](../planning/lifecycle.md) - How plans link to PRs
- [Graphite Integration](../erk/graphite-integration.md) - Stack metadata
- [Stub PR Workflow Link](stub-pr-workflow-link.md) - Three-tier PR body lifecycle in one-shot workflows
