---
audit_result: edited
last_audited: "2026-02-08"
read_when:
  - modifying trigger-async-learn orchestration
  - debugging why learn materials are missing or malformed in CI
  - understanding the local-to-gist-to-codespace data flow
title: Async Learn Local Preprocessing
tripwires:
  - action: adding subprocess calls to trigger-async-learn
    warning:
      This command uses direct Python function calls, not subprocess invocations.
      This is intentional — see the direct-call architecture section below.
  - action: preprocessing remote sessions locally
    warning:
      Remote sessions are already preprocessed. Only local sessions (source_type
      == 'local') go through local preprocessing.
---

# Async Learn Local Preprocessing

## Why Local Preprocessing Exists

Before PR #6460, `trigger-async-learn` uploaded raw session logs and let the GitHub Actions codespace preprocess them. This added ~30s of startup time to every learn run because codespace environments are slow for I/O-heavy preprocessing (reading large JSONL files, deduplicating entries, generating XML).

Moving preprocessing to the developer's local machine eliminates this overhead. The codespace receives already-compressed XML and can start agent analysis immediately. This shifts compute from billed CI time to free local time.

## Direct-Call Architecture

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, trigger_async_learn -->

The `trigger-async-learn` command imports functions directly from sibling exec scripts rather than invoking them as subprocesses. This is a deliberate architectural choice:

| Approach                                                             | Trade-off                                                                                                              |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| Subprocess (`erk exec get-learn-sessions`)                           | Clean isolation but adds process startup overhead per step, requires JSON parsing between steps, and loses type safety |
| Direct import (`from .get_learn_sessions import _discover_sessions`) | Shared process, immediate dict access, type-checked — but couples the scripts at import time                           |

The direct-call approach won because `trigger-async-learn` orchestrates 6 tightly-coupled steps in sequence where each step's output feeds the next. The overhead of 6 subprocess roundtrips with JSON serialization/deserialization was measurable.

**Anti-pattern**: Don't add new subprocess invocations to this orchestrator. If you need a new step, add it as a direct function call following the existing pattern.

## Session Classification: Planning vs Implementation

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, trigger_async_learn -->

During preprocessing, each session is classified as either `"planning"` or `"impl"` based on whether its session ID matches the `planning_session_id` from the plan's GitHub metadata. This classification becomes the filename prefix (e.g., `planning-abc123.xml` vs `impl-def456.xml`), which downstream learn agents use to weight insights differently — planning sessions contain design rationale, while implementation sessions contain execution details.

**Only local sessions are preprocessed.** Remote sessions (from gists) arrive already preprocessed. The preprocessing loop skips any session where `source_type != "local"`.

## Material Assembly Pipeline

The learn materials directory (`.erk/scratch/learn-{issue_number}`) is a staging area that accumulates three types of files before gist upload:

1. **Preprocessed session XML** — from local session preprocessing
2. **PR review comments** — inline code review threads serialized as JSON
3. **PR discussion comments** — top-level PR conversation serialized as JSON

PR comments are fetched via gateway calls, not `gh` CLI. This matters because the gateway provides typed results with LBYL error handling (checking `isinstance(result, PRNotFound)` rather than catching exceptions), consistent with erk's error handling patterns.

**Graceful degradation**: If no PR exists for the plan issue, comment fetching is skipped entirely. Missing PR comments don't block the learn workflow — sessions alone contain sufficient material for insight extraction.

All files are packed into a single gist using the delimiter-based format described in [Gist Materials Interchange](../architecture/gist-materials-interchange.md), then the gist URL is passed to the `learn.yml` workflow via `workflow_dispatch`.

## Preprocessing Pipeline Internals

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, _preprocess_session_direct -->

The local preprocessing pipeline (`_preprocess_session_direct`) replicates the same logic as the `preprocess-session` CLI command but as a direct function call. It processes both the main session log and any discovered agent logs (subagent sessions), applying the same filtering chain to each:

1. Empty and warmup sessions are filtered out entirely
2. Documentation blocks are deduplicated (same doc loaded multiple times)
3. Tool parameters are truncated (large file contents in tool calls)
4. Assistant messages are deduplicated (repeated system prompts)

Agent logs are discovered via the session's directory structure and included in the output with a `agent-` source label prefix. This ensures subagent reasoning is captured alongside the main session.

The pipeline reports compression metrics to stderr — typical reduction is ~99% (e.g., 6.2M → 67k chars), confirming that preprocessing is working correctly.

## Related Documentation

- [Gist Materials Interchange](../architecture/gist-materials-interchange.md) — Delimiter-based file packing format used in Step 5
- [Session Preprocessing](../sessions/preprocessing.md) — What preprocessing does to session XML
- [Learn Workflow](learn-workflow.md) — Complete async learn flow and agent tier architecture
