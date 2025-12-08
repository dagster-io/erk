---
title: Two-Phase Submission Architecture
read_when:
  - "understanding preflight AI finalize pattern"
  - "implementing PR submission workflows"
  - "structuring submission phases"
  - "working with PreflightResult"
---

# Two-Phase Submission Architecture

The preflight → AI → finalize pattern for PR submission workflows.

## Pattern Overview

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Preflight  │ ──▶ │  AI Analysis │ ──▶ │  Finalize   │
│  (Python)   │     │   (Agent)    │     │  (Python)   │
└─────────────┘     └──────────────┘     └─────────────┘
```

## Phase Responsibilities

### Preflight (Python)

- Verify prerequisites (auth, branch state)
- Gather data for AI analysis (diffs)
- Create draft PR if needed
- Return structured `PreflightResult`

### AI Analysis (Agent)

- Analyze diff content
- Generate commit message (title + body)
- Only semantic work - no bash, no side effects
- Return structured message

### Finalize (Python)

- Update PR with AI-generated content
- Add footer, closing references
- Post comments to issues
- Cleanup temp files

## Benefits

1. **Testability**: Python phases use FakeGit/FakeGitHub
2. **Reliability**: Auth/push errors caught before AI cost
3. **Cost**: Smaller agent = fewer tokens
4. **Speed**: Preflight can fail fast

## Implementation

Both git and Graphite flows use this pattern:

- Graphite: `erk_shared/integrations/gt/operations/`
- Git: `erk_shared/integrations/git_pr/operations/`
