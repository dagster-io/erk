# Plan: Add AGENTS.md Guidance to Prevent Raw JSONL in Context

## Context

When Claude Code runs background agents via the `Task` tool, `TaskOutput` sometimes returns raw JSONL session transcripts (hundreds of lines of JSON with UUIDs, timestamps, tool calls) instead of clean text summaries. This wastes thousands of context tokens and makes output unreadable. Observed in a codespace session where Explore agents returned full session transcripts to the parent.

## Change

**File**: `AGENTS.md` (modify)

Add guidance in the "How Agents Work" section about background agent output safety:

- Background agents must NEVER return raw session JSONL to the parent context
- Raw JSONL is identifiable by: `"parentUuid"`, `"isSidechain"`, `"sessionId"` fields
- If TaskOutput returns raw JSONL instead of clean text, discard it and summarize from what the agent already knows
- The purpose of background agents is to protect the parent context from verbose output — dumping raw transcripts defeats this

## Verification

Review the AGENTS.md change reads naturally and the guidance is clear.