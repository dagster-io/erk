---
title: Session Preprocessing Architecture
read_when:
  - "modifying session preprocessing or compression pipeline"
  - "understanding why there are two preprocessing implementations"
  - "linking sessions to plans for learn workflow"
  - "debugging preprocessing failures or empty session output"
tripwires:
  - action: "adding a new filtering step to preprocess_session.py"
    warning: "There are TWO preprocessing implementations: the exec script (preprocess_session.py) and erk-shared (session_preprocessing.py). The exec script has the full filtering pipeline; erk-shared has only Stage 1 mechanical reduction. New filters go in the exec script. Read this doc first."
  - action: "calling preprocess_session functions from trigger_async_learn"
    warning: "trigger_async_learn duplicates the exec script's filtering pipeline as _preprocess_session_direct(). If you change the exec script's pipeline, update the direct function too."
  - action: "passing session content to an analysis agent"
    warning: "Raw JSONL sessions can be 6+ million characters. Always preprocess first. The learn workflow validates preprocessed output exists before spawning agents."
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Session Preprocessing Architecture

## Two-Stage Design

Session preprocessing uses a two-stage architecture to separate deterministic operations from semantic judgment:

<!-- Source: packages/erk-shared/src/erk_shared/learn/extraction/session_preprocessing.py -->

**Stage 1 (Deterministic)** — in `erk_shared.learn.extraction.session_preprocessing` — performs mechanical reduction that is always correct: dropping `file-history-snapshot` entries, stripping usage metadata, removing empty text blocks, deduplicating verbatim-repeated assistant messages, and converting to compressed XML via `SessionXmlWriter`.

<!-- Source: packages/erk-shared/src/erk_shared/learn/extraction/llm_distillation.py, distill_with_haiku -->

**Stage 2 (Semantic)** — in `erk_shared.learn.extraction.llm_distillation` — delegates judgment calls to Haiku via Claude Code subprocess (piggybacks on its auth). Haiku handles noise detection, semantic deduplication, and verbose output pruning. The prompt is intentionally conservative: "when in doubt, RETAIN the content" — especially error messages, stack traces, and debugging steps.

**Why two stages?** Stage 1 is fast, local, and predictable — suitable for running in bulk without API calls. Stage 2 is expensive but handles cases where mechanical rules would either over-prune (removing semantically important content) or under-prune (missing near-duplicate blocks that differ only in whitespace/formatting).

## Two Implementations Problem

There are two separate preprocessing codepaths that must stay in sync:

<!-- Source: src/erk/cli/commands/exec/scripts/preprocess_session.py, preprocess_session -->

1. **Exec script** (`erk exec preprocess-session`) — the full CLI command with all filters: empty session detection, warmup filtering, documentation deduplication, parameter truncation, tool result pruning, log discovery operation filtering, and token-budget chunking.

<!-- Source: packages/erk-shared/src/erk_shared/learn/extraction/session_preprocessing.py, preprocess_session -->

2. **Shared library** (`erk_shared.learn.extraction.session_preprocessing.preprocess_session()`) — only Stage 1 mechanical reduction. No empty/warmup detection, no doc dedup, no parameter truncation, no tool result pruning.

<!-- Source: src/erk/cli/commands/exec/scripts/trigger_async_learn.py, _preprocess_session_direct -->

Additionally, `trigger_async_learn` contains `_preprocess_session_direct()` which duplicates the exec script's full pipeline as direct Python function calls (to avoid subprocess overhead when preprocessing multiple sessions in sequence). This is a third copy of the orchestration logic.

**Why the duplication?** The exec script is designed for CLI invocation (reading file paths, writing temp files). The shared library serves `SessionStore`-based workflows that work with content strings. The `trigger_async_learn` direct function avoids subprocess overhead in batch operations. This is acknowledged tech debt — the filtering pipeline should ideally be unified.

## Filtering Pipeline

When filtering is enabled, the exec script applies these steps in order:

1. **Session ID filtering** — JSONL files can contain entries from multiple sessions (shared log files). Entries not matching the target session ID are skipped. Session ID defaults to the filename stem.
2. **File-history-snapshot removal** — These entries are pure metadata noise.
3. **Log discovery operation filtering** — Removes `pwd`, `ls ~/.claude`, `find ~/.claude` Bash commands that are implementation mechanics, not semantic content.
4. **Empty session detection** — Sessions with fewer than 3 entries or lacking both user messages and assistant responses are skipped entirely.
5. **Warmup session detection** — Sessions where the first user message contains "warmup" are skipped (these are boilerplate acknowledgment sessions).
6. **Documentation deduplication** — Repeated command documentation blocks (identified by content hash) are replaced with reference markers after the first occurrence.
7. **Parameter truncation** — Tool parameters longer than 200 chars are truncated, with special handling for file paths (preserves first 2 and last 2 path segments).
8. **Assistant message deduplication** — When an assistant message has both text and tool_use, and the text is identical to the previous assistant message's text, the duplicate text is dropped (keeps only tool_use).
9. **Tool result pruning** — Results longer than 30 lines are truncated to first 30 lines, but error-containing lines from the remainder are preserved.

**The order matters.** Empty/warmup detection runs before deduplication and truncation so that trivial sessions are rejected cheaply before more expensive processing.

## Session-Plan Linkage

The learn workflow needs to know which sessions belong to which plan. This linkage is stored in GitHub issue metadata, not in the session files themselves:

<!-- Source: packages/erk-shared/src/erk_shared/sessions/discovery.py, find_sessions_for_plan -->

`find_sessions_for_plan()` extracts session IDs from plan-header metadata blocks (`created_from_session` for planning, `last_local_impl_session` for implementation) and from issue comments (`impl-started`/`impl-ended` events for all implementation sessions, `learn-invoked` for learn sessions).

The planning session ID is captured at plan creation time by the `session_id_injector_hook`, which writes the current session ID to `.erk/scratch/current-session-id`. This is then embedded in the plan issue's metadata when the issue is created.

## Agent Log Discovery

<!-- Source: src/erk/cli/commands/exec/scripts/preprocess_session.py, discover_agent_logs -->
<!-- Source: src/erk/cli/commands/exec/scripts/preprocess_session.py, discover_planning_agent_logs -->

Claude Code sessions spawn subagents whose logs live alongside the main session as `agent-*.jsonl` files in the same directory. Two discovery strategies exist:

- **All agents** (`discover_agent_logs`) — matches agent logs by session ID (checks first entry's `sessionId` field). Used for general preprocessing.
- **Planning agents only** (`discover_planning_agent_logs`) — finds Task tool invocations with `subagent_type="Plan"` in the parent session, then correlates agent log timestamps within 1-second windows. Used when only plan-phase reasoning matters.

The temporal correlation approach in `discover_planning_agent_logs` is fragile (relies on sub-second timestamp matching) but necessary because Claude Code doesn't write agent type metadata into agent log files.

## Token Budget and Chunking

<!-- Source: src/erk/cli/commands/exec/scripts/preprocess_session.py, split_entries_to_chunks -->

Token estimation uses a rough 4-characters-per-token heuristic. The default chunk size for the learn workflow is 20,000 tokens (via `--max-tokens`), chosen to stay under Claude's 25,000-token read limit with margin.

Chunking splits at entry boundaries (never mid-entry). Each chunk is independently valid XML with its own `<session>` wrapper. Multi-part files are named `{prefix}-{session-id}-part{N}.xml`.

## Session Source Abstraction

<!-- Source: packages/erk-shared/src/erk_shared/learn/extraction/session_source.py, SessionSource -->

Sessions originate from two sources (local `~/.claude/projects/` and remote GitHub Actions), but are always processed locally as files on disk. The `SessionSource` ABC tracks _origin_ (for attribution), not _location_. Remote sessions are downloaded before preprocessing, at which point they become local files — the source abstraction remembers they came from remote for proper filtering and deduplication.

## Integration with erk land

<!-- Source: src/erk/cli/commands/land_learn.py -->

`erk land` displays session preprocessing stats alongside each session in its output. This reuses the exec script's filtering pipeline via direct Python imports (no subprocess).

### SessionStats Dataclass

<!-- Source: src/erk/cli/commands/land_learn.py, SessionStats -->

`SessionStats` is a frozen dataclass with four fields:

- `user_turns`: Count of user messages with non-empty text content
- `duration_minutes`: Computed from min/max entry timestamps, rounded to nearest minute. `None` if fewer than 2 timestamps found.
- `raw_size_kb`: Total bytes of main JSONL file plus all discovered agent logs, divided by 1024
- `xml_size_kb`: Total bytes of final compressed XML output after full filtering pipeline, divided by 1024

### \_compute_session_stats()

Reuses the exec script's pipeline via direct imports from `erk.cli.commands.exec.scripts.preprocess_session` (importing `deduplicate_assistant_messages`, `deduplicate_documentation_blocks`, `discover_agent_logs`, `is_empty_session`, `is_warmup_session`, `process_log_file`, `split_entries_to_chunks`, `truncate_tool_parameters`).

Uses `max_tokens=200_000` (not the default 20k) to capture complete statistics without aggressive chunking. Applies the full pipeline: `process_log_file()` -> deduplication filters -> `split_entries_to_chunks()` for each session and its agent logs.

### Output Format

Stats are displayed in Rich markup:

```
[dim]12 turns · 8 min  (515 KB → 89 KB)[/dim]
```

- Duration part is omitted when `duration_minutes` is `None`
- KB values use comma separators for readability (`:,` format)
- Graceful fallback: if stats computation fails, shows simple file size only

## Related Documentation

- [Session Preprocessing](../sessions/preprocessing.md) — CLI usage patterns, compression metrics, and file naming conventions
- [Learn Workflow](learn-workflow.md) — Full learn pipeline that consumes preprocessed sessions
- [Scratch Storage](scratch-storage.md) — Where preprocessed output is stored
