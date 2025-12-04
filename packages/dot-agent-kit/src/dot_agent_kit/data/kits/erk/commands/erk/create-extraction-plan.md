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

Parse the context argument (if provided) for:

1. **Session IDs** - Look for patterns like "session abc123" or UUID-like strings
2. **Steering context** - Remaining text provides focus for the extraction analysis

**If no explicit session IDs provided:**

Run the session discovery helper with size filtering to exclude tiny sessions:

```bash
dot-agent run erk list-sessions --min-size 1024
```

The JSON output includes:

- `branch_context.is_on_trunk`: Whether on main/master branch
- `current_session_id`: Current session ID from SESSION_CONTEXT env
- `sessions`: List of recent sessions with metadata (only meaningful sessions >= 1KB)
- `project_dir`: Path to session logs
- `filtered_count`: Number of tiny sessions filtered out

**Behavior based on branch context:**

**If `branch_context.is_on_trunk` is true (on main/master):**

Use `current_session_id` only. Skip user prompt - analyze current conversation.

**If `branch_context.is_on_trunk` is false (feature branch):**

First, determine if the current session is "trivial" (< 1KB, typically just launching a command like this one). Check if the current session appears in the filtered results - if not, it was filtered out as tiny.

**Common pattern**: User launches a fresh session solely to run `/erk:create-extraction-plan` on substantial work from a previous session. In this case, auto-select the substantial session(s) without prompting.

**If current session is tiny AND exactly 1 substantial session exists:**

Auto-select the substantial session without prompting. Briefly inform user:

> "Auto-selected session [id] (current session is trivial, analyzing the substantial session)"

**If current session is tiny AND 2+ substantial sessions exist:**

Auto-select ALL substantial sessions without prompting. Briefly inform user:

> "Auto-selected [N] sessions (current session is trivial, analyzing all substantial sessions)"

**If current session is substantial AND exactly 1 total session (itself):**

Proceed with current session analysis. No prompt needed.

**If current session is substantial AND other substantial sessions exist:**

Present sessions to user for selection:

> "Found these sessions for this worktree:
>
> 1. [Dec 3, 11:38 AM] 4f852cdc... - how many session ids does... (current)
> 2. [Dec 3, 11:35 AM] d8f6bb38... - no rexporting due to backwards...
> 3. [Dec 3, 11:28 AM] d82e9306... - /gt:pr-submit
>
> Which sessions should I analyze? (1=current only, 2=all, or list session numbers like '1,3')"

Wait for user selection before proceeding.

**If 0 sessions remain after filtering (all tiny including current):**

Use current session only despite being tiny. Inform user:

> "No meaningful sessions found (all sessions were < 1KB). Analyzing current conversation anyway."

**If explicit session IDs found in context:**

Load and preprocess the session logs. Session logs are stored in `project_dir` as flat files:

- Main sessions: `<session-id>.jsonl`
- Agent logs: `agent-<agent-id>.jsonl`

Match session IDs against filenames (full or partial prefix match), then preprocess:

```bash
dot-agent run erk preprocess-session <project-dir>/<session-id>.jsonl --stdout
```

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

### Step 6: Format Plan Content

Format the selected suggestions as an implementation plan:

```markdown
# Plan: Documentation Extraction from Session

## Objective

Extract documentation improvements identified from session analysis.

## Source Information

- **Source Plan Issues:** [List issue numbers if analyzing a plan session, or empty list]
- **Extraction Session IDs:** ["<session-id>"]

## Documentation Items

### Item 1: [Title from suggestion]

**Type:** [Agent Doc | Skill | Glossary entry | etc.]
**Location:** `[path]`
**Action:** [New doc | Update existing | Merge into]
**Priority:** [High | Medium | Low]

**Content:**
[The draft content from the suggestion]

### Item 2: [Title]

...
```

### Step 7: Create Extraction Plan Issue

Extract the session ID from the `SESSION_CONTEXT` hook reminder in your context, then run the kit CLI command with the plan content directly:

```bash
dot-agent run erk create-extraction-plan \
    --plan-content="<the formatted plan content>" \
    --session-id="<session-id>" \
    --extraction-session-ids="<session-id>"
```

The command automatically:

1. Writes the plan to `.erk/scratch/<session-id>/extraction-plan-*.md`
2. Creates a GitHub issue with `erk-plan` + `erk-extraction` labels
3. Sets `plan_type: extraction` in the plan-header metadata
4. Includes `source_plan_issues` and `extraction_session_ids` for tracking

Parse the JSON result to get `issue_number` and `issue_url`.

**Note:** The current session ID (from `SESSION_CONTEXT` reminder) is used both as the `--session-id` for scratch storage and in `--extraction-session-ids` metadata.

### Step 7.5: Verify Issue Structure

Run the plan check command to validate the issue conforms to Schema v2:

```bash
erk plan check <issue_number>
```

This validates:

- plan-header metadata block present in issue body
- plan-header has required fields
- First comment exists
- plan-body content extractable from first comment

**If verification fails:** Display the check output and warn the user that the issue may need manual correction.

### Step 8: Output Next Steps

After issue creation and verification, display:

```
✅ Extraction plan created and saved to GitHub

**Issue:** [title]
           [issue_url]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the extraction:
    erk implement [issue_number]

Submit for remote implementation:
    erk submit [issue_number]
```

---

## Output

After analysis (and user confirmation if applicable), display suggestions using the output format from the analysis guide, then proceed to create the extraction plan issue.
