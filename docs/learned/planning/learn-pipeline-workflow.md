---
title: Learn Pipeline Workflow
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
read_when:
  - debugging why learn materials are missing or malformed
  - understanding data flow from sessions to documentation plan
  - choosing between local learn and async learn modes
  - adding a new stage to the learn pipeline
tripwires:
  - action: "adding a new pipeline stage to the async learn pipeline"
    warning: "New stages must be direct Python function calls, not subprocess invocations. The orchestrator uses tight coupling for performance. See the Direct-Call Architecture section in planned-pr-context-local-preprocessing.md."
  - action: "changing how sessions are classified as planning vs impl"
    warning: "Classification uses planning_session_id from GitHub metadata. The resulting prefix (planning- vs impl-) propagates into XML filenames and is used by downstream learn agents to weight insights differently."
  - action: "modifying how learn materials are committed to a branch"
    warning: "The CI workflow checks out the learn branch and reads materials from .erk/sessions/. File names and directory structure must match what learn.yml expects."
---

# Learn Pipeline Workflow

## Purpose

This document covers the **data pipeline** that moves session logs from local disk to a GitHub Actions agent. For the agent orchestration, status tracking, and `/erk:learn` skill details, see [Learn Workflow](learn-workflow.md). For the preprocessing internals, see [Planned PR Context Local Preprocessing](planned-pr-context-local-preprocessing.md).

## Pipeline Architecture

The learn pipeline has 7 stages that transform raw session JSONL into a documentation plan. The key architectural decision is **where processing happens**: stages 1-5 run locally (fast, free), while stages 6-7 run in GitHub Actions (background, billed).

```
Local machine                              GitHub Actions
┌────────────────────────────────────┐    ┌──────────────────────┐
│ 1. Discover sessions               │    │ 6. Agent execution   │
│ 2. Preprocess → XML                │    │ 7. PR review/merge   │
│ 3. Fetch PR comments (optional)    │    └──────────────────────┘
│ 4. Commit materials to learn branch│              ▲
│ 5. Trigger learn.yml workflow ─────┼──────────────┘
└────────────────────────────────────┘
```

This split exists because preprocessing is I/O-heavy (reading large JSONL files, deduplicating entries) and was adding ~30s of startup time when done in CI. Local machines handle it instantly.

## Two Modes: Local vs Async

| Aspect          | Local (`/erk:learn`)       | Async (upload-impl-session pipeline)                |
| --------------- | -------------------------- | --------------------------------------------------- |
| **Stages run**  | All 7 on developer machine | Upload only local; all stages run in GitHub Actions |
| **Use case**    | Quick iteration, debugging | Background processing after landing                 |
| **Blocking**    | Yes — holds terminal       | No — returns immediately after upload               |
| **Git context** | Full (branch, worktree)    | None in CI (relies on learn branch materials)       |
| **API quota**   | Developer's                | GitHub-managed                                      |

The async path was designed for the `erk land` flow, where learn runs automatically after a PR merges without blocking the developer.

## Stage-by-Stage Data Flow

### Stage 1: Session Discovery

<!-- Source: src/erk/cli/commands/exec/scripts/get_learn_sessions.py, _discover_sessions -->

Finds all session logs related to a plan by querying GitHub issue metadata for tracked session IDs, then resolving those IDs to local file paths. Three session source types exist:

- **Local sessions** — JSONL files under `~/.claude/projects/<repo>/sessions/`
- **Branch-based sessions** — preprocessed sessions accumulated on `planned-pr-context/{plan_id}` branches (from local and remote stages)
- **Legacy artifact sessions** — sessions from older CI runs stored as workflow artifacts

The discovery function also has a **local fallback**: when GitHub has no tracked sessions for a plan, it scans the 10 most recent local sessions as candidates. This handles cases where session tracking was added after implementation began.

### Stage 2: Session Preprocessing

<!-- Source: src/erk/cli/commands/exec/scripts/preprocess_session.py, preprocess_session -->

Transforms raw JSONL session logs into compressed XML. **Both local and remote sessions** go through the same `preprocess_session()` pipeline (in `src/erk/cli/commands/exec/scripts/preprocess_session.py`, unified in PR #6974). Remote sessions are first downloaded via the `download-remote-session` exec command, which fetches session content from a git branch and saves it locally, then the downloaded file is preprocessed identically to local sessions.

The filtering chain applies in order:

1. Empty/warmup session detection → skip entirely
2. Documentation block deduplication (by content hash)
3. Tool parameter truncation (200 char limit)
4. Assistant message deduplication
5. Agent log discovery and inclusion

Tool result pruning (30 line limit, error lines preserved) occurs during XML generation, not as a preprocessing filter step.

Typical compression: **~99%** (e.g., 6.2M → 67k chars). Each session is classified as `planning` or `impl` based on whether its session ID matches the `planning_session_id` from GitHub metadata. This classification becomes the filename prefix, which downstream agents use to weight insights differently.

Output files are token-limited (20k tokens per chunk) to stay under Claude's read limit, producing either `{prefix}-{session-id}.xml` or `{prefix}-{session-id}-part{N}.xml` for large sessions.

### Stage 3: PR Comment Fetching (Optional)

Fetches PR review threads and discussion comments via gateway calls (not `gh` CLI). This stage is intentionally lenient — if no PR exists for the plan, it skips silently rather than failing. Three reasons:

1. Plan might not have a PR yet (just created)
2. Implementation might be in progress
3. In GitHub Actions, there's no git context for branch-to-PR resolution

Both review threads (inline code comments) and discussion comments (top-level conversation) are serialized as JSON files in the learn directory.

### Stage 4: Commit Materials to Learn Branch

Commits all learn materials (session XMLs, PR comment JSONs) to a dedicated git branch `planned-pr-context/{plan_id}`. The branch is created from `origin/master`, files are written to `.erk/sessions/` using git plumbing (`commit_files_to_branch`), and the branch is force-pushed. Force-push enables idempotent re-learn scenarios.

This replaced the earlier gist-based transport (removed in commit 12f964cb5) which required delimiter-based file packing and custom upload/download scripts. The git-based approach stores individual files at standard paths, making them visible in GitHub's UI and readable by CI without custom parsing.

### Stage 5: Workflow Trigger

Triggers `learn.yml` via `workflow_dispatch` with the `learn_branch` (containing materials in `.erk/sessions/`) and plan ID. The workflow uses concurrency groups (`learn-plan-{plan_id}`) with `cancel-in-progress: true`, so re-triggering learn for the same plan cancels any in-progress run.

### Stage 6: Agent Execution

<!-- Source: .github/workflows/learn.yml -->

The GitHub Actions workflow checks out the learn branch (which contains materials under `.erk/sessions/`), sets up erk, and runs `/erk:learn`. The agent reads materials directly from the filesystem, then orchestrates the multi-agent analysis pipeline described in [Learn Workflow](learn-workflow.md#agent-tier-architecture).

The workflow runs with `claude-opus-4-6` as the base model, though individual agents within `/erk:learn` may override to different models for specific steps.

### Stage 7: PR Review and Merge

Human reviews the learn plan, optionally edits it, and submits for implementation through the standard `plan-implement` workflow.

## Failure Modes

| Stage                | Failure              | Behavior                                                                 |
| -------------------- | -------------------- | ------------------------------------------------------------------------ |
| 1 (Discovery)        | No sessions found    | Warning, continues with empty list; local fallback scans recent sessions |
| 2 (Preprocessing)    | Empty/warmup session | Silently filtered out                                                    |
| 2 (Preprocessing)    | Malformed JSONL      | Logged, file skipped                                                     |
| 3 (PR Comments)      | No PR exists         | Skipped entirely (lenient)                                               |
| 4 (Branch Commit)    | Push failure         | **Pipeline fails** — learn branch is required for async path             |
| 5 (Workflow Trigger) | Workflow not found   | Fails with error about missing `learn.yml`                               |
| 6 (Agent Execution)  | Agent crashes        | CI job fails, no retry                                                   |

The key design choice: stages 1-3 are lenient (degrade gracefully), while stage 4 is strict (fails the pipeline). This is because sessions alone contain sufficient material for insight extraction, but without the learn branch there's no way to deliver materials to CI.

## Debugging

For local pipeline issues, stages 1-2 have corresponding `erk exec` commands that can be run independently:

```bash
# Stage 1: Test session discovery
erk exec get-learn-sessions <issue>

# Stage 2: Test preprocessing
erk exec preprocess-session <session-path> --stdout
```

Note: `upload-impl-session` uploads a session JSONL file to a git branch — it is not a debugging tool for stages 3-5.

For CI issues (stage 6), use `gh run view <run-id>` to inspect workflow logs.

## Related Documentation

- [Planned PR Context Local Preprocessing](planned-pr-context-local-preprocessing.md) — Direct-call architecture, session classification, preprocessing internals
- [Learn Workflow](learn-workflow.md) — Agent tier architecture, status tracking, /erk:learn skill
- [Session Preprocessing](../sessions/preprocessing.md) — What preprocessing does to session XML
- [Learn Plan Land Flow](../cli/learn-plan-land-flow.md) — Integration with PR landing
