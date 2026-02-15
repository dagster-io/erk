---
title: Learn Pipeline Workflow
last_audited: "2026-02-08"
audit_result: clean
read_when:
  - debugging why learn materials are missing or malformed
  - understanding data flow from sessions to documentation plan
  - choosing between local learn and async learn modes
  - adding a new stage to the learn pipeline
tripwires:
  - action: "adding a new pipeline stage to trigger-async-learn"
    warning: "New stages must be direct Python function calls, not subprocess invocations. The orchestrator uses tight coupling for performance. See the Direct-Call Architecture section in async-learn-local-preprocessing.md."
  - action: "changing how sessions are classified as planning vs impl"
    warning: "Classification uses planning_session_id from GitHub metadata. The resulting prefix (planning- vs impl-) propagates into XML filenames and is used by downstream learn agents to weight insights differently."
  - action: "modifying the gist upload content format"
    warning: "The download side (download-learn-materials) parses delimiters to split content back into files. Changes to the upload format must be mirrored in the download parser. See gist-materials-interchange.md."
---

# Learn Pipeline Workflow

## Purpose

This document covers the **data pipeline** that moves session logs from local disk to a GitHub Actions agent. For the agent orchestration, status tracking, and `/erk:learn` skill details, see [Learn Workflow](learn-workflow.md). For the preprocessing internals, see [Async Learn Local Preprocessing](async-learn-local-preprocessing.md).

## Pipeline Architecture

The learn pipeline has 7 stages that transform raw session JSONL into a documentation plan issue. The key architectural decision is **where processing happens**: stages 1-5 run locally (fast, free), while stages 6-7 run in GitHub Actions (background, billed).

```
Local machine                              GitHub Actions
┌────────────────────────────────────┐    ┌──────────────────────┐
│ 1. Discover sessions               │    │ 6. Agent execution   │
│ 2. Preprocess → XML                │    │ 7. PR review/merge   │
│ 3. Fetch PR comments (optional)    │    └──────────────────────┘
│ 4. Upload all materials to gist    │              ▲
│ 5. Trigger learn.yml workflow ─────┼──────────────┘
└────────────────────────────────────┘
```

This split exists because preprocessing is I/O-heavy (reading large JSONL files, deduplicating entries) and was adding ~30s of startup time when done in CI. Local machines handle it instantly.

## Two Modes: Local vs Async

| Aspect          | Local (`/erk:learn`)       | Async (`erk exec trigger-async-learn`) |
| --------------- | -------------------------- | -------------------------------------- |
| **Stages run**  | All 7 on developer machine | 1-5 local, 6-7 in GitHub Actions       |
| **Use case**    | Quick iteration, debugging | Background processing after landing    |
| **Blocking**    | Yes — holds terminal       | No — returns immediately after trigger |
| **Git context** | Full (branch, worktree)    | None in CI (relies on gist metadata)   |
| **API quota**   | Developer's                | GitHub-managed                         |

The async path was designed for the `erk land` flow, where learn runs automatically after a PR merges without blocking the developer.

## Stage-by-Stage Data Flow

### Stage 1: Session Discovery

<!-- Source: src/erk/cli/commands/exec/scripts/get_learn_sessions.py, _discover_sessions -->

Finds all session logs related to a plan issue by querying GitHub issue metadata for tracked session IDs, then resolving those IDs to local file paths. Three session source types exist:

- **Local sessions** — JSONL files under `~/.claude/projects/<repo>/sessions/`
- **Remote gist-based sessions** — preprocessed sessions uploaded to GitHub gists (from remote implementation)
- **Legacy artifact sessions** — sessions from older CI runs stored as workflow artifacts

The discovery function also has a **local fallback**: when GitHub has no tracked sessions for a plan, it scans the 10 most recent local sessions as candidates. This handles cases where session tracking was added after implementation began.

### Stage 2: Session Preprocessing

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, lines 409-460 -->

Transforms raw JSONL session logs into compressed XML. **Both local and remote sessions** go through the same `_preprocess_session_direct()` pipeline (unified in PR #6974). Remote sessions are first downloaded via `_download_remote_session_for_learn()`, which fetches the gist content and saves it as `{session_id}.jsonl` in a `remote-downloads/` subdirectory, then the downloaded file is preprocessed identically to local sessions.

The filtering chain applies in order:

1. Empty/warmup session detection → skip entirely
2. Documentation block deduplication (by content hash)
3. Tool parameter truncation (200 char limit)
4. Tool result pruning (30 line limit, error lines preserved)
5. Assistant message deduplication
6. Agent log discovery and inclusion

Typical compression: **~99%** (e.g., 6.2M → 67k chars). Each session is classified as `planning` or `impl` based on whether its session ID matches the `planning_session_id` from GitHub metadata. This classification becomes the filename prefix, which downstream agents use to weight insights differently.

Output files are token-limited (20k tokens per chunk) to stay under Claude's read limit, producing either `{prefix}-{session-id}.xml` or `{prefix}-{session-id}-part{N}.xml` for large sessions.

### Stage 3: PR Comment Fetching (Optional)

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, trigger_async_learn -->

Fetches PR review threads and discussion comments via gateway calls (not `gh` CLI). This stage is intentionally lenient — if no PR exists for the plan, it skips silently rather than failing. Three reasons:

1. Plan might not have a PR yet (just created)
2. Implementation might be in progress
3. In GitHub Actions, there's no git context for branch-to-PR resolution

Both review threads (inline code comments) and discussion comments (top-level conversation) are serialized as JSON files in the learn directory.

### Stage 4: Gist Upload

<!-- Source: src/erk/cli/commands/exec/scripts/upload_learn_materials.py, combine_learn_material_files -->

Bundles all learn materials into a single gist using a delimiter-based format. The gateway only supports single-file gists, so multiple files (session XMLs, PR comment JSONs) are concatenated with `=`-delimited headers. The download side parses these delimiters to reconstruct individual files.

This is a **critical failure point** — if gist upload fails, the entire async pipeline stops. The local learn path bypasses this by reading files directly.

For the delimiter format specification, see [Gist Materials Interchange](../architecture/gist-materials-interchange.md).

### Stage 5: Workflow Trigger

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, trigger_async_learn -->

Triggers `learn.yml` via `workflow_dispatch` with the gist URL and issue number. The workflow uses concurrency groups (`learn-issue-{N}`) with `cancel-in-progress: true`, so re-triggering learn for the same issue cancels any in-progress run.

### Stage 6: Agent Execution

<!-- Source: .github/workflows/learn.yml -->

The GitHub Actions workflow checks out the repo, sets up erk, and runs `/erk:learn` with the gist URL. The agent downloads materials from the gist, then orchestrates the multi-agent analysis pipeline described in [Learn Workflow](learn-workflow.md#agent-tier-architecture).

The workflow runs with `claude-haiku-4-5` as the base model, though individual agents within `/erk:learn` may override to higher models for quality-critical synthesis steps.

### Stage 7: PR Review and Merge

Human reviews the learn plan issue, optionally edits it, and submits for implementation through the standard `plan-implement` workflow.

## Failure Modes

| Stage                | Failure              | Behavior                                                                 |
| -------------------- | -------------------- | ------------------------------------------------------------------------ |
| 1 (Discovery)        | No sessions found    | Warning, continues with empty list; local fallback scans recent sessions |
| 2 (Preprocessing)    | Empty/warmup session | Silently filtered out                                                    |
| 2 (Preprocessing)    | Malformed JSONL      | Logged, file skipped                                                     |
| 3 (PR Comments)      | No PR exists         | Skipped entirely (lenient)                                               |
| 4 (Gist Upload)      | API failure          | **Pipeline fails** — gist is required for async path                     |
| 5 (Workflow Trigger) | Workflow not found   | Fails with error about missing `learn.yml`                               |
| 6 (Agent Execution)  | Agent crashes        | CI job fails, no retry                                                   |

The key design choice: stages 1-3 are lenient (degrade gracefully), while stage 4 is strict (fails the pipeline). This is because sessions alone contain sufficient material for insight extraction, but without the gist there's no way to deliver materials to CI.

## Debugging

For local pipeline issues (stages 1-5), each stage has a corresponding `erk exec` command that can be run independently:

```bash
# Test each stage in isolation
erk exec get-learn-sessions <issue>
erk exec preprocess-session <session-path> --stdout
erk exec upload-learn-materials --learn-dir <dir> --issue <N>
erk exec trigger-async-learn <issue>
```

For CI issues (stage 6), use `gh run view <run-id>` to inspect workflow logs.

## Related Documentation

- [Async Learn Local Preprocessing](async-learn-local-preprocessing.md) — Direct-call architecture, session classification, preprocessing internals
- [Learn Workflow](learn-workflow.md) — Agent tier architecture, status tracking, /erk:learn skill
- [Gist Materials Interchange](../architecture/gist-materials-interchange.md) — Delimiter-based file packing format
- [Session Preprocessing](../sessions/preprocessing.md) — What preprocessing does to session XML
- [Learn Plan Land Flow](../cli/learn-plan-land-flow.md) — Integration with PR landing
