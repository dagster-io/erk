---
description: Create an extraction plan for documentation improvements
---

# /erk:create-extraction-plan

Analyzes session context to identify documentation gaps and creates an extraction plan issue to track the improvements.

## Usage

```bash
/erk:create-extraction-plan [context]
```

**Arguments:**

- `[context]` - Optional. Free-form text that can specify:
  - Session ID(s) to analyze (e.g., "session abc123")
  - Focus/steering for extraction (e.g., "focus on CLI patterns")
  - Or both (e.g., "sessions abc123 and def456, focus on testing")

**Examples:**

```bash
# Analyze current conversation
/erk:create-extraction-plan

# Current conversation with focus
/erk:create-extraction-plan "focus on the CLI patterns we discussed"

# Analyze specific session log
/erk:create-extraction-plan "session abc123"

# Multiple sessions with steering
/erk:create-extraction-plan "sessions abc123 and def456, focus on testing patterns"
```

## What It Does

1. Analyzes session(s) for documentation gaps
2. Identifies both learning gaps (Category A) and teaching gaps (Category B)
3. Creates a GitHub issue with `erk-plan` + `erk-extraction` labels
4. Outputs next steps for implementation

## What You'll Get

Suggestions organized by category:

**Category A (Learning Gaps):**

- Documentation that would have made the session faster
- Usually agent docs or skills for patterns/workflows

**Category B (Teaching Gaps):**

- Documentation for what was BUILT in the session
- Usually glossary entries, routing updates, reference updates

---

## Agent Instructions

You are creating an extraction plan from session analysis.

### Step 0: Determine Source and Context

Parse the context argument (if provided) to determine:

1. **Session IDs** - Look for patterns like "session abc123" or UUID-like strings
2. **Steering context** - Remaining text provides focus for the extraction analysis

**If session IDs found:**

Load and preprocess the session logs:

```bash
# Get the project directory for this codebase
dot-agent run erk find-project-dir
```

The JSON output includes `session_logs` (list of session files) and `latest_session_id`. Session logs are stored directly in the project directory as flat files:

- Main sessions: `<session-id>.jsonl`
- Agent logs: `agent-<agent-id>.jsonl`

Match session IDs against filenames (full or partial prefix match), then preprocess:

```bash
dot-agent run erk preprocess-session <project-dir>/<session-id>.jsonl --stdout
```

**If no session IDs found:**

Analyze the current conversation. Use steering context (if any) to focus the analysis.

### Step 0.5: Verify Existing Documentation

Before analyzing gaps, scan the project for existing documentation:

```bash
# Check for existing agent docs
ls -la docs/agent/ 2>/dev/null || echo "No docs/agent/ directory"

# Check for existing skills
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"

# Check root-level docs
ls -la *.md README* CONTRIBUTING* 2>/dev/null
```

Create a mental inventory of what's already documented. For each potential suggestion later, verify it doesn't substantially overlap with existing docs.

### Step 1-4: Analyze Session

@../../docs/erk/includes/extract-docs-analysis-shared.md

### Step 5: Confirm with User

**If analyzing current conversation (no session IDs in context):**

Ask for confirmation before proceeding:

> "Based on this session, I identified these potential documentation gaps:
>
> 1. [Brief title] - [One sentence why]
> 2. [Brief title] - [One sentence why]
> 3. ...
>
> Which of these would be valuable for future sessions? I'll generate detailed suggestions and draft content for the ones you select."

Wait for user response before generating full output.

**If analyzing session logs (session IDs were specified):**

Skip confirmation and output all suggestions immediately since the user explicitly chose to analyze specific session(s).

### Step 6-8: Create Extraction Plan Issue

@../../docs/erk/includes/extract-plan-workflow-shared.md

**Note:** Use the current session ID (from `SESSION_CONTEXT` reminder) as `<session-id>` in the extraction plan metadata.

---

## Output

After analysis (and user confirmation if applicable), display suggestions using the output format from the analysis guide, then proceed to create the extraction plan issue.
