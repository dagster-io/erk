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

### Source Discovery Behavior

The learn command discovers sessions through multiple code paths:

1. **Gist path**: Download from provided gist_url
2. **Local path**: Scan ~/.claude/projects/ for JSONL files
3. **Remote path**: Fetch from CI artifacts or stored locations

These paths may return different session counts. A planning session from one path may be unavailable in another. This is expected and handled gracefully.

**Authoritative source:** Use `erk exec get-learn-sessions` to get the canonical list of available sessions for a given plan. This command centralizes session source logic and returns consistent results.

## XML Output Structure

The preprocessed output uses XML with sections for:

- Tool invocations and their results
- Agent decisions and reasoning
- File modifications
- Error encounters and recoveries

This structured format enables analysis agents to efficiently extract patterns without parsing raw conversation logs.

## Size Validation

Sessions larger than 100k characters **must** be preprocessed before passing to analysis agents. The learn command validates that preprocessed output exists before spawning agents. If preprocessing fails or produces malformed output, learn agents will fail to extract meaningful data.

## Token Budget Details

The preprocessing command enforces a 20k token limit by default:

```bash
erk exec preprocess-session --session-file <path> --output <path> --max-tokens 20000
```

**Budget behavior:**

- Sessions within budget: Single XML output file
- Sessions exceeding budget: Automatic chunking to multiple files
- Each chunk is independently valid XML
- Downstream agents receive list of chunk paths

**Monitoring guidance:**

- Target: XML output should stay under 22k tokens (20k content + 2k structure)
- If chunking occurs frequently, consider increasing `--max-tokens` or reducing input session size
- Token overruns are handled gracefully via chunking, not as errors

## Preprocessing Failure Recovery

Preprocessing can fail for certain sessions (corrupted, truncated, malformed JSONL). This is expected behavior:

- Failed sessions are skipped
- Remaining sessions continue processing
- Learn pipeline proceeds with available data
- No retry or manual intervention required

This resilience ensures a single bad session doesn't block the entire learn workflow.

## Multipart Handling

Very large sessions may be automatically chunked during preprocessing. Each chunk is independently valid XML. The learn workflow handles reassembly transparently.

## Planning Session ID

The learn workflow needs to associate sessions with their parent plan. The planning session ID is extracted during preprocessing and stored in the output metadata. This enables the learn command to link extracted insights back to the plan that generated them.

## Related Topics

- [Learn Workflow](learn-workflow.md) — Full learn workflow including session preprocessing validation
- [Scratch Storage](scratch-storage.md) — Where preprocessed output is stored
