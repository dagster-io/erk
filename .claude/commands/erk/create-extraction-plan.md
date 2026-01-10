---
description: Create an extraction plan for documentation improvements
---

# /erk:create-extraction-plan

Analyzes session context to identify documentation gaps and creates an extraction plan issue to track the improvements.

## Prerequisites

Before running this command, ensure `docs/learned/` exists and has at least one documentation file:

```bash
# Initialize docs/learned if it doesn't exist
erk docs init

# Verify it's ready
ls docs/learned/*.md
```

If `docs/learned/` is missing or empty, the command will fail with a suggestion to run `erk docs init` first.

**Note:** Running `erk init` for a new project automatically initializes `docs/learned/` with template files (glossary.md, conventions.md, guide.md).

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
2. Uploads preprocessed session XML to a secret gist for review
3. Identifies both learning gaps (Category A) and teaching gaps (Category B)
4. Creates a GitHub issue with `erk-plan` + `erk-extraction` labels
5. Outputs next steps for implementation

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

### Step 1: Determine Source and Context

Parse the context argument (if provided) for:

1. **Session IDs** - Look for patterns like "session abc123" or UUID-like strings
2. **Steering context** - Remaining text provides focus for the extraction analysis

**If no explicit session IDs provided:**

Run the session discovery helper to get all sessions with branch metadata:

```bash
erk exec list-sessions
```

The JSON output includes:

- `branch_context.current_branch`: The current git branch
- `branch_context.is_on_trunk`: Whether on main/master branch
- `current_session_id`: Current session ID from SESSION_CONTEXT env
- `sessions`: List of recent sessions with metadata including `branch` field
- `project_dir`: Path to session logs

**Behavior based on branch context:**

**If `branch_context.is_on_trunk` is true (on main/master):**

Use `current_session_id` only. Skip user prompt - analyze current conversation.

**If `branch_context.is_on_trunk` is false (feature branch):**

Filter sessions by branch: only include sessions where `session.branch` matches `branch_context.current_branch`.

**If 0 sessions match the current branch:**

Use current session only. Inform user:

> "No sessions found for branch [branch-name]. Analyzing current conversation."

**If 1+ sessions match the current branch:**

Auto-select ALL matching sessions without prompting. Briefly inform user:

> "Found [N] session(s) for branch [branch-name]"

This approach eliminates the size-based heuristics - branch filtering is more precise and ensures we only analyze work relevant to the current feature.

**If explicit session IDs found in context:**

Load and preprocess the session logs. Session logs are stored in `project_dir` as flat files:

- Main sessions: `<session-id>.jsonl`
- Agent logs: `agent-<agent-id>.jsonl`

Match session IDs against filenames (full or partial prefix match), then preprocess:

```bash
erk exec preprocess-session <project-dir>/<session-id>.jsonl --stdout
```

### Step 1.5: Upload Raw Materials to Gist

After determining which session(s) to analyze, upload the preprocessed session XML to a secret gist for user review.

**For each selected session:**

1. Create scratch directory and preprocess the session to XML:

   ```bash
   mkdir -p .erk/scratch/sessions/<session-id>
   erk exec preprocess-session <project-dir>/<session-id>.jsonl --stdout > .erk/scratch/sessions/<session-id>/session.xml
   ```

2. Create a secret gist with all preprocessed session files:

   ```bash
   gh gist create --secret --desc "Extraction plan raw materials: <session-ids>" .erk/scratch/sessions/*/session.xml
   ```

3. Capture the gist URL from the output and display to the user:

   ```
   📋 Raw materials uploaded to gist for review:
      <gist-url>

   Proceeding with analysis...
   ```

4. **Save the gist URL** for inclusion in the extraction plan issue (Step 11)

5. Continue with Step 2

**Note:** This step allows users to review the raw session content that will be analyzed. The gist is secret (not publicly discoverable) but shareable via URL.

### Step 2: Check for Associated Plan Issue Session Content

If on a feature branch (not trunk), check if this branch has an associated plan issue:

```bash
# Check if .impl/issue.json exists
cat .impl/issue.json 2>/dev/null
```

**If issue.json exists AND has valid `issue_number`:**

1. Extract the `issue_number` from the JSON response
2. Attempt to extract session content from the plan issue:
   ```bash
   erk exec extract-session-from-issue <issue_number> --stdout
   ```
3. If session XML is returned (not an error), store it as "plan issue session content"
4. Note the session IDs from the stderr JSON output

**If issue.json doesn't exist OR extraction fails:** Continue with session log analysis only (this is normal for branches not created via `erk implement`).

### Step 3: Verify Existing Documentation

Before analyzing gaps, scan the project for existing documentation:

```bash
# Check for existing agent docs
ls -la docs/learned/ 2>/dev/null || echo "No docs/learned/ directory"

# Check for existing skills
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"

# Check root-level docs
ls -la *.md README* CONTRIBUTING* 2>/dev/null
```

Create a mental inventory of what's already documented. For each potential suggestion later, verify it doesn't substantially overlap with existing docs.

### Step 4: Mine Full Session Context

**CRITICAL**: Session analysis must examine the FULL conversation, not just recent messages.

**Compaction Awareness:**

Long sessions may have been "compacted" - earlier messages summarized to save context. However:

- The pre-compaction messages are still part of the SAME LOGICAL CONVERSATION
- Valuable research, discoveries, and reasoning often occurred BEFORE compaction
- Look for compaction markers and explicitly include pre-compaction content in your analysis
- Session logs (`.jsonl` files) contain the full uncompacted conversation

**Subagent Mining:**

The Task tool spawns specialized subagents (Explore, Plan, etc.) that often do the most valuable work:

1. **Identify all Task tool invocations** - Look for `<invoke name="Task">` blocks
2. **Read subagent outputs** - Each Task returns a detailed report with discoveries
3. **Mine Explore agents** - These do codebase exploration and document what they found
4. **Mine Plan agents** - These reason through approaches and capture design decisions
5. **Don't just summarize** - Extract the specific insights, patterns, and learnings discovered

**What to look for in subagent outputs:**

- Files they read and what they learned from them
- Patterns they discovered in the codebase
- Design decisions they reasoned through
- External documentation they fetched (WebFetch, WebSearch)
- Comparisons between different approaches

**Example mining:**

If a Plan agent's output contains:

> "The existing provider pattern in data/provider.py uses ABC with abstract methods.
> This follows erk's fake-driven testing pattern where FakeProvider implements the same interface."

This indicates:

- ABC pattern documentation might need updating
- The fake-driven-testing skill connection was discovered
- This is Category A (learning) if not documented, or confirms existing docs if it is

### Steps 5-8: Analyze Session

@../../../.erk/docs/kits/erk/includes/extract-docs-analysis-shared.md

### Step 9: Combine Session Sources

When both **plan issue session content** (from Step 2) AND **session logs** (from Step 1) are available, analyze them together:

**Plan Issue Session Content** (from Step 2):

- Contains the PLANNING session - research, exploration, design decisions
- Look for: external docs consulted, codebase patterns discovered, trade-offs considered
- Particularly valuable for **Category A (Learning Gaps)** - what would have made planning faster

**Session Logs** (from Step 1):

- Contains the IMPLEMENTATION session(s) - actual work done
- Look for: features built, patterns implemented, problems solved
- Particularly valuable for **Category B (Teaching Gaps)** - documentation for what was built

When presenting analysis, clearly label which source revealed each insight:

- "[Plan session]" for insights from the plan issue
- "[Impl session]" for insights from session logs

### Step 10: Confirm with User

**If analyzing current conversation (no session IDs in context):**

Present findings neutrally and let the user decide value:

> "Based on this session, I identified these potential documentation gaps:
>
> 1. [Brief title] - [One sentence why]
> 2. [Brief title] - [One sentence why]
> 3. ...
>
> Which of these would be valuable for future sessions? I'll generate detailed suggestions and draft content for the ones you select."

**IMPORTANT: Do NOT editorialize about whether gaps are "worth" documenting, "minor", "not broadly applicable", etc. Present findings neutrally and let the user decide. Your job is to surface potential gaps, not gatekeep what's valuable.**

Wait for user response before generating full output.

**If analyzing session logs (session IDs were specified):**

Skip confirmation and output all suggestions immediately since the user explicitly chose to analyze specific session(s).

### Step 11: Format Plan Content

Format the selected suggestions as an implementation plan with this structure:

- **Objective**: Brief statement of what documentation will be added/improved
- **Source Information**: Session ID(s) that were analyzed
- **Raw Materials**: Link to the gist containing preprocessed session XML (from Step 1.5)
- **Documentation Items**: Each suggestion should include:
  - Type (Category A or B)
  - Location (where in the docs structure)
  - Action (add, update, create)
  - Priority (based on effort and impact)
  - Content (the actual draft content)

### Step 12: Create Extraction Plan Issue

**CRITICAL: Use this exact CLI command. Do NOT use `gh issue create` directly.**

Get the session ID from the `SESSION_CONTEXT` reminder in your conversation context.

```bash
erk exec create-extraction-plan \
    --plan-content="<the formatted plan content>" \
    --session-id="<session-id-from-SESSION_CONTEXT>" \
    --extraction-session-ids="<comma-separated-session-ids-that-were-analyzed>"
```

This command automatically:

1. Writes plan to `.erk/scratch/<session-id>/extraction-plan.md`
2. Creates GitHub issue with `erk-plan` + `erk-extraction` labels
3. Sets `plan_type: extraction` in plan-header metadata

**Note:** The current session ID (from `SESSION_CONTEXT` reminder) is used as `--session-id` for scratch storage. The `--extraction-session-ids` should list all session IDs that were analyzed (may differ from current session).

### Step 13: Verify and Output

Run verification to ensure the issue was created with proper Schema v2 compliance:

```bash
erk plan check <issue_number>
```

Display next steps:

```
✅ Extraction plan saved to GitHub

**Issue:** [title from result]
           [url from result]

**Next steps:**

View the plan:
    gh issue view [issue_number] --web

Implement the plan:
    erk implement [issue_number]

Submit for remote implementation:
    erk plan submit [issue_number]
```

---

## Output

After analysis (and user confirmation if applicable), display suggestions using the output format from the analysis guide, then proceed to create the extraction plan issue.
