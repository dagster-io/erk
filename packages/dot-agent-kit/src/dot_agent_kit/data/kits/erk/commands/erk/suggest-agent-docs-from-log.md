---
description: Analyze a session log to suggest documentation improvements
---

# /erk:suggest-agent-docs-from-log

Analyzes a session log file (by session ID) to identify documentation gaps and suggest new agent docs or skills that would make future sessions more efficient.

## Usage

```bash
/erk:suggest-agent-docs-from-log <session-id>
```

**Arguments:**

- `<session-id>` - Full or partial (first 8 chars) session ID to analyze

Run this command to review past sessions for:

- Repeated explanations that could be pre-loaded docs
- Trial-and-error patterns indicating missing guidance
- Extensive codebase exploration for core patterns
- Architecture discoveries that should be documented
- Workflow corrections suggesting unclear conventions
- External research that could be local documentation

## What You'll Get

A structured list of documentation suggestions, each with:

- **Title**: Descriptive name for the doc
- **Type**: Agent Doc (`docs/agent/`) or Skill (`.claude/skills/`)
- **Action**: New doc, update existing, or merge into existing
- **Priority**: Effort/impact assessment
- **Rationale**: Why this session suggests the doc is needed
- **Draft content**: Skeleton ready to be fleshed out

---

## Agent Instructions

You are analyzing a session log file to identify patterns that suggest missing documentation.

### Step 0: Load and Preprocess Session Log

First, find the project directory and locate the session log:

```bash
# Get the project directory for this codebase
dot-agent run erk find-project-dir
```

The output contains the project directory path (e.g., `/Users/name/.claude/projects/-Users-name-code-myproject`).

Next, list session logs to find one matching the provided session ID:

```bash
# List recent sessions for this project
ls -la <project-dir>/sessions/
```

Session directories are named by session ID (e.g., `70e91b45-c320-442f-9ddc-7122098285ce/`).

Match the provided session ID argument:

- If full ID provided: exact match
- If partial ID (8+ chars): prefix match

Once you find the matching session directory, preprocess it:

```bash
# Preprocess the session log for analysis
dot-agent run erk preprocess-session <project-dir>/sessions/<session-id>/logs/ --stdout
```

This outputs compressed XML with:

- Tool calls and results (most recent per batch)
- User messages
- Assistant responses
- Correlated agent subprocess logs (via `--include-agents` default)

### Step 1-4: Analyze Session

@../../docs/erk/includes/suggest-docs-analysis-shared.md

### Step 5: Output Suggestions Directly

**Note:** Unlike `/erk:suggest-agent-docs`, this command skips the confirmation step and outputs all suggestions immediately since the user explicitly chose to analyze a specific session.

---

## Output

Display suggestions using the output format from the analysis guide above. Replace "Based on this session" with "Based on session `<session-id>`" in the header.
