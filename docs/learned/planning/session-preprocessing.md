---
title: Session Preprocessing Architecture
read_when:
  - "preprocessing sessions for learn workflow"
  - "understanding token budget for session analysis"
  - "working with session XML format"
---

# Session Preprocessing Architecture

Session preprocessing converts raw Claude Code session logs (JSONL) into compressed XML suitable for agent analysis. This is a required step before running learn workflow agents.

## Why Preprocessing is Required

Raw session logs can be extremely large (6+ million characters). Agent context windows cannot handle this volume. Preprocessing achieves ~99% token reduction (e.g., 6.2M → 67k characters) while preserving the semantically important content.

## Preprocessing Command

```bash
erk exec preprocess-session --session-file <path> --output <path>
```

The command:

1. Reads raw JSONL session log
2. Extracts tool calls, decisions, and key conversation turns
3. Produces structured XML output
4. Validates output is within agent context budget

## Session Source Types

Sessions come from different sources:

- **Local sessions**: From `~/.claude/projects/` (JSONL format)
- **Uploaded sessions**: From gist storage (for remote/CI sessions)
- **Multipart sessions**: Large sessions that span multiple files

## XML Output Structure

The preprocessed output uses XML with sections for:

- Tool invocations and their results
- Agent decisions and reasoning
- File modifications
- Error encounters and recoveries

This structured format enables analysis agents to efficiently extract patterns without parsing raw conversation logs.

## Size Validation

Sessions larger than 100k characters **must** be preprocessed before passing to analysis agents. The learn command validates that preprocessed output exists before spawning agents. If preprocessing fails or produces malformed output, learn agents will fail to extract meaningful data.

## Multipart Handling

Very large sessions may be automatically chunked during preprocessing. Each chunk is independently valid XML. The learn workflow handles reassembly transparently.

## Planning Session ID

The learn workflow needs to associate sessions with their parent plan. The planning session ID is extracted during preprocessing and stored in the output metadata. This enables the learn command to link extracted insights back to the plan that generated them.

## Related Topics

- [Learn Workflow](learn-workflow.md) — Full learn workflow including session preprocessing validation
- [Scratch Storage](scratch-storage.md) — Where preprocessed output is stored
