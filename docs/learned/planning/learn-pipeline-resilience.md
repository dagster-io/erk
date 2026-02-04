---
title: Learn Pipeline Resilience Patterns
read_when:
  - "debugging why learn command fell back to local sessions"
  - "understanding gist download failures in learn workflow"
  - "session discovery returning unexpected results"
tripwires:
  - action: "running /erk:learn with gist_url that returns empty"
    warning: "Empty gist indicates preprocessing hasn't completed. This triggers silent fallback to local session discovery. Verify gist upload succeeded or provide no gist_url to skip remote sources."
  - action: "relying on planning_session_id being available locally"
    warning: "Planning sessions may be from earlier branch/run and unavailable locally. Use erk exec get-learn-sessions to verify availability; missing sessions don't block pipeline."
---

# Learn Pipeline Resilience Patterns

The learn pipeline is designed to degrade gracefully when expected data sources are unavailable. Understanding these fallback behaviors helps distinguish expected behavior from actual errors.

## Gist Fallback Pattern

When `/erk:learn` receives a `gist_url` parameter but the gist is empty:

1. The system attempts to download preprocessed materials from the gist
2. Empty response triggers fallback to local session discovery
3. Local sessions are discovered via `erk exec get-learn-sessions`
4. Preprocessing runs locally on discovered JSONL files

**Why this happens:** The `gist_url` is stored in plan metadata before preprocessing completes. On first learn run, the gist may not yet be populated.

**Expected behavior:** This fallback is intentional and does not indicate an error. The learn pipeline continues with locally available data.

## Session Discovery Differences

Sessions come from multiple sources with different availability:

| Source                         | Availability                | Notes                           |
| ------------------------------ | --------------------------- | ------------------------------- |
| Local implementation sessions  | Current branch's ~/.claude/ | Always available if run locally |
| Remote implementation sessions | Gist or CI artifacts        | Available after upload          |
| Planning sessions              | May be from earlier branch  | Often unavailable locally       |

The `planning_session_id` in plan metadata points to the session that created the plan. This session may be:

- From an earlier branch (already merged/deleted)
- From a different worktree
- Only available in remote storage

**Expected behavior:** Missing planning sessions do not block the learn pipeline. Proceed with available sessions.

## Error vs Expected Behavior

| Symptom                             | Type     | Response                                |
| ----------------------------------- | -------- | --------------------------------------- |
| Gist download returns empty         | Expected | Fallback to local                       |
| Planning session not in local paths | Expected | Skip, continue with available           |
| Preprocessing fails on one session  | Expected | Skip that session, continue with others |
| All sessions unavailable            | Error    | No data to analyze; investigate         |

## Related Documentation

- [Learn Workflow](learn-workflow.md) - Full learn workflow architecture
- [Session Preprocessing](session-preprocessing.md) - Token budgets and chunking
