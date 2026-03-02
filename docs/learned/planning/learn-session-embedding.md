---
title: Learn Session Embedding
read_when:
  - "embedding session XML files in learn plan PRs"
  - "working with session preprocessing in the land or plan-save pipeline"
  - "debugging missing session XML in learn plan diffs"
---

# Learn Session Embedding

Session XML files are embedded in learn plan PR diffs so that async learn agents have access to the full session context. Two independent codepaths produce these files, converging on the same `create_plan_draft_pr(extra_files=...)` parameter.

## Codepath 1: plan_save.py (`--session-xml-dir` flag)

<!-- Source: src/erk/cli/commands/exec/scripts/plan_save.py, _save_as_planned_pr -->

See `_save_as_planned_pr()` in `src/erk/cli/commands/exec/scripts/plan_save.py` for the session embedding logic. The `plan_save.py` exec script accepts a `--session-xml-dir` Click option pointing to a directory of pre-generated XML files. The script globs XML files from that directory in sorted order for deterministic ordering and places each under `.erk/impl-context/sessions/{filename}` in the PR diff.

This codepath is used by the `/erk:learn` skill (Step 7), which preprocesses sessions into XML files in a temp directory before calling `plan_save.py`.

## Codepath 2: land_learn.py (inline preprocessing)

<!-- Source: src/erk/cli/commands/land_learn.py:43-51, 68-154, 209-305 -->

The `land_learn.py` command preprocesses sessions inline rather than reading from a directory.

<!-- Source: src/erk/cli/commands/land_learn.py, SessionStats -->

See `SessionStats` in `src/erk/cli/commands/land_learn.py` for the frozen dataclass capturing preprocessing metrics. The `xml_chunks` field holds the actual XML content strings produced by the preprocessing pipeline.

### Preprocessing Pipeline

The preprocessing function runs the full pipeline for a single session:

1. Reads the JSONL session log
2. Counts user turns and computes duration from timestamps
3. Runs preprocessing (deduplication, truncation)
4. Chunks XML output at a 200,000 token limit
5. Returns stats or `None` if preprocessing fails

### Session Discovery

Returns `dict[str, str]` mapping file paths to XML content. This dict is passed directly to `create_plan_draft_pr(extra_files=...)`.

**File naming convention:** `{type}-{session_id}.xml` with `-part{N}` suffix for multi-chunk sessions.

**Type prefixes:** `planning`, `impl`, `learn`, `unknown` — derived from the session's role in the plan lifecycle.

### Agent log discovery

Agent logs (from subagent sessions) are discovered alongside primary sessions and included in the XML embedding.

## Shared Infrastructure

Both codepaths converge on `create_plan_draft_pr(extra_files=...)`. The `extra_files` parameter accepts `dict[str, str]` mapping relative paths to content. Files are committed alongside the plan markdown in the draft PR.

## File Inventory Logging

The file inventory logger reports all files committed to the learn plan PR with paths and sizes, using human-readable formatting.

## Related Documentation

- [Land-Learn Integration](../cli/land-learn-integration.md) — The land command's learn workflow
- [Learn Workflow](learn-workflow.md) — Full learn pipeline documentation
