---
title: PR Submit Workflow Phases
read_when:
  - "understanding the erk pr submit workflow"
  - "debugging PR submission issues"
  - "working with AI-generated PR descriptions"
  - "understanding plan context integration in PRs"
---

# PR Submit Workflow Phases

The `erk pr submit` command uses a 6-phase workflow to submit PRs with AI-generated descriptions. This document explains each phase and the two-layer architecture.

## Two-Layer Architecture

The workflow has two layers:

1. **Core layer (always runs)**: `git push` + `gh pr create` - works without Graphite
2. **Graphite layer (optional)**: `gt submit` for stack metadata - runs when Graphite is available and branch is tracked

## Workflow Phases

| Phase | Name                      | Description                                  |
| ----- | ------------------------- | -------------------------------------------- |
| 1     | Creating or Updating PR   | Push changes and create/find PR              |
| 2     | Getting diff              | Extract diff from GitHub API for AI analysis |
| 3     | Fetching plan context     | Get plan from linked erk-plan issue          |
| 4     | Generating PR description | AI generates title and body via Claude CLI   |
| 5     | Graphite enhancement      | Add stack metadata (if available)            |
| 6     | Updating PR metadata      | Push AI-generated title/body to GitHub       |

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

### Phase 2: Getting diff

- Uses GitHub API to get PR diff
- Saves diff to session scratch directory for AI processing
- Includes all commits since parent branch

### Phase 3: Fetching plan context

**This phase integrates plan context into PR generation.**

The `PlanContextProvider` checks for a linked erk-plan issue:

1. Looks for `.impl/issue.json` in repo root
2. Extracts issue number from metadata
3. Fetches plan body from GitHub
4. Includes objective summary if linked

**Output**: Plan context is passed to the AI generator in Phase 4, enabling the AI to understand the original intent and produce better PR descriptions.

Example console output:

```
Phase 3: Fetching plan context
   Incorporating plan from issue #5828
   Linked to Objective: Documentation improvements
```

Or if no plan is found:

```
Phase 3: Fetching plan context
   No linked plan found
```

### Phase 4: Generating PR description

- Uses `CommitMessageGenerator` with Claude CLI
- Inputs: diff file, commit messages, branch info, **plan context**
- Outputs: AI-generated title and body

The plan context from Phase 3 helps the AI:

- Match PR description to original intent
- Include relevant context from the plan
- Reference objective if applicable

### Phase 5: Graphite enhancement

Only runs in standard flow (skipped if Graphite-first flow was used):

- Checks if Graphite is available and authenticated
- Runs `gt submit` to add stack metadata
- Generates Graphite stack URL

This phase is non-fatal - errors are warnings, not failures.

### Phase 6: Updating PR metadata

- Updates PR title and body via GitHub API
- Uses AI-generated content from Phase 4
- Links to Graphite if available

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

## Related Topics

- [Commit Message Generation](commit-message-generation.md) - AI generation details
- [Plan Lifecycle](../planning/lifecycle.md) - How plans link to PRs
- [Graphite Integration](../erk/graphite-integration.md) - Stack metadata
