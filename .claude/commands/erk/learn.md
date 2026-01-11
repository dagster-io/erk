---
description: Extract insights from plan-associated sessions
argument-hint: "[issue-number]"
---

# /erk:learn

Create a documentation plan from Claude Code sessions associated with a plan implementation. The verb "learn" means: analyze what happened, extract insights, and create an actionable plan to document those learnings.

## Usage

```
/erk:learn           # Infers issue from current branch (P{issue}-...)
/erk:learn 4655      # Explicit issue number
```

## Agent Instructions

### Step 1: Get Session Information

Run the learn command to get session details:

```bash
erk learn <issue-number> --json --no-track
```

Parse the JSON output to get:

- `session_paths`: Paths to readable session files
- `planning_session_id`: Session that created the plan
- `implementation_session_ids`: Sessions that executed the plan
- `local_session_ids`: Fallback sessions found locally (when GitHub has no tracked sessions)

If no sessions are found (both `session_paths` empty and `local_session_ids` empty), inform the user and stop.

### Step 2: Extract Plan Issue Session Content

Attempt to extract session content embedded in the plan issue itself:

```bash
erk exec extract-session-from-issue <issue-number> --stdout
```

This returns the planning session XML that was attached to the issue when it was created (via `erk implement` workflow). This content contains:

- Research and exploration done during planning
- Design decisions and trade-offs considered
- External documentation consulted

**Note:** This may overlap with `planning_session_id` from Step 1, but the issue-embedded content is authoritative. If extraction fails (no embedded content), continue with session logs only.

### Step 3: Check Existing Documentation

Before extracting insights, scan for existing documentation to avoid suggesting duplicates:

```bash
ls -la docs/learned/ 2>/dev/null || echo "No docs/learned/ directory"
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"
```

Create a mental inventory of what's already documented. For each potential insight later, verify it doesn't substantially overlap with existing docs.

### Step 4: Preprocess and Upload Session Content

For each session path from Step 1, preprocess it to compressed XML format:

```bash
mkdir -p .erk/scratch/sessions
erk exec preprocess-session <session-path> --stdout > .erk/scratch/sessions/<session-id>.xml
```

Also save the plan issue session content (from Step 2) if it was retrieved:

```bash
erk exec extract-session-from-issue <issue-number> --stdout > .erk/scratch/sessions/plan-issue-<issue-number>.xml
```

#### Upload Raw Materials to Gist

Upload all preprocessed session files to a secret gist:

```bash
gh gist create --desc "Learn materials for plan #<issue-number>" .erk/scratch/sessions/*.xml
```

Capture the gist URL and display to user:

```
Raw materials uploaded: <gist-url>
```

**Save the gist URL** for inclusion in the plan issue.

### Step 5: Deep Session Analysis

Read the preprocessed XML files and mine them thoroughly.

**Compaction Awareness:**

Long sessions may have been "compacted" - earlier messages summarized. However:

- Pre-compaction content is still part of the same logical conversation
- Valuable research often occurred BEFORE compaction
- Session logs contain the full uncompacted conversation

**Subagent Mining:**

The Task tool spawns subagents that do valuable work:

1. **Identify all Task tool invocations** - Look for `<invoke name="Task">` blocks
2. **Read subagent outputs** - Each returns a detailed report
3. **Mine Explore agents** - Codebase exploration findings
4. **Mine Plan agents** - Design decisions and reasoning
5. **Extract specific insights** - Don't just summarize

**What to capture:**

- Files read and what was learned from them
- Patterns discovered in the codebase
- Design decisions and reasoning
- External documentation fetched (WebFetch, WebSearch)
- Comparisons between approaches
- Error messages and how they were resolved

**Analysis Questions:**

- What was the user trying to accomplish?
- What approaches were tried?
- What challenges were encountered?
- What solutions worked?

### Step 6: Extract Documentation Items

Based on session analysis, identify documentation to create:

**Category A (Learning Gaps)** - Would have made the session faster:

- Patterns that required discovery
- Gotchas that caused confusion
- Non-obvious solutions

**Category B (Teaching Gaps)** - Documentation for what was built:

- New features or commands
- Architectural decisions made
- Conventions established

For each item, capture:

- What document to create/update
- Where it belongs (docs/learned/, .claude/skills/, etc.)
- Draft content with specific examples from the session

### Step 7: Present Findings for Validation

Present your findings to the user with:

1. **Summary of insights** with source attribution:
   - **[Plan]** - From planning/research phase
   - **[Impl]** - From implementation phase

2. **Proposed documentation items** - What you plan to include in the issue

3. **Ask for validation** - Are there insights to add, remove, or refine?

### Step 8: Create Documentation Plan Issue

**CRITICAL: Front-load context into the issue.**

Include context you've gathered so the implementing agent doesn't have to rediscover it. This saves tokens and speeds up execution. Include in the issue body:

1. **Rich context section** with:
   - Key files and their purposes (that you discovered)
   - Patterns found in the codebase
   - Relevant existing documentation
   - Any external resources consulted
   - Specific code examples from sessions

2. **Raw materials link** - The gist URL from Step 4

3. **Documentation items** - Each with:
   - Location (file path)
   - Action (create/update)
   - Draft content (as complete as possible)
   - Source (which session/insight it came from)

Get the session ID from the `SESSION_CONTEXT` reminder.

```bash
erk exec create-extraction-plan \
    --plan-content="<the formatted plan content>" \
    --session-id="<session-id-from-SESSION_CONTEXT>" \
    --extraction-session-ids="<comma-separated-session-ids-that-were-analyzed>"
```

Display the result:

```
Documentation plan created: <issue-url>
Raw materials: <gist-url>
```

### Tips

- Preprocessed sessions use XML: `<user>`, `<assistant>`, `<tool_use>`, `<tool_result>`
- `<tool_result>` elements with errors often reveal the most useful insights
- The more context you include in the issue, the faster the implementing agent can work
- Don't be stingy with context - include file contents, code snippets, and reasoning
