---
title: Slash Command Simplification
read_when:
  - "optimizing slash commands for fewer LLM calls"
  - "reducing token cost of commands"
  - "moving orchestration from commands to CLI"
---

# Slash Command Simplification

## The Problem

Complex slash commands can require 5-7+ LLM turns to:

1. Parse context (session IDs, paths)
2. Run validation commands
3. Execute core CLI command
4. Parse JSON output
5. Create marker files
6. Format and display results

Each turn costs tokens and adds latency.

## The Solution: CLI Self-Sufficiency

Move orchestration logic INTO the CLI command, so the slash command becomes a single bash call.

### Before (Multi-Turn Orchestration)

```markdown
# /erk:save-plan (140 lines)

### Step 1: Get Session ID

Extract session ID from SESSION_CONTEXT reminder...

### Step 2: Validate Prerequisites

Run git and gh auth checks...

### Step 3: Save Plan

Run CLI with --session-id flag...

### Step 4: Create Marker File

mkdir -p .erk/scratch/<SESSION_ID> && touch ...

### Step 5: Format Output

Display success message with next steps...
```

**Cost**: 5-7 LLM turns, high token usage

### After (Single CLI Call)

```markdown
# /erk:save-plan (19 lines)

Run this command and display the output:

\`\`\`bash
dot-agent run erk plan-save-to-issue --format display
\`\`\`

On success, display the URL and next steps from output.
```

**Cost**: 1 LLM turn, minimal tokens

## How to Achieve This

1. **File-based context**: Hook persists session ID to file, CLI reads it
2. **CLI creates markers**: Move marker file creation into CLI success path
3. **Display format option**: Add `--format display` for human-readable output
4. **Self-contained validation**: CLI validates prerequisites internally

## When to Simplify

Consider simplification when a slash command:

- Has 3+ sequential steps
- Requires parsing intermediate output
- Creates files/markers after CLI calls
- Could benefit from `--format display` option

## Trade-offs

| Aspect      | Multi-Turn    | Single CLI     |
| ----------- | ------------- | -------------- |
| Token cost  | High          | Minimal        |
| Latency     | 5-10 seconds  | 1-2 seconds    |
| Flexibility | LLM can adapt | Fixed behavior |
| Debugging   | Visible steps | Opaque CLI     |
