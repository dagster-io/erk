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

Run the exec script to get session details:

```bash
erk exec get-learn-sessions <issue-number>
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
mkdir -p .erk/scratch/sessions/<current-session-id>/learn
erk exec preprocess-session <session-path> --stdout > .erk/scratch/sessions/<current-session-id>/learn/<session-id>.xml
```

Note: `<current-session-id>` is the session running `/erk:learn`, `<session-id>` is the session being preprocessed.

Also save the plan issue session content (from Step 2) if it was retrieved:

```bash
erk exec extract-session-from-issue <issue-number> --stdout > .erk/scratch/sessions/<current-session-id>/learn/plan-issue.xml
```

#### Upload Raw Materials to Gist

Upload all preprocessed session files to a secret gist:

```bash
gh gist create --desc "Learn materials for plan #<issue-number>" .erk/scratch/sessions/<current-session-id>/learn/*.xml
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

Based on session analysis, identify documentation to create.

**CRITICAL: Filter out execution discipline issues.**

Before proposing any documentation item, ask: "Was this information in the code the agent was directly working with?"

**NOT documentation candidates** (execution discipline issues):

- Agent didn't read class/function signature before calling it
- Agent assumed API shape instead of checking type hints
- Agent didn't read the file they were modifying
- Agent made wrong assumptions that reading the immediate code would have prevented
- General language/framework knowledge (pytest patterns, Python stdlib, etc.)

These errors indicate the implementing agent should have explored the code they were touching more carefully.

**IS documentation candidate** (learning gap):

- Pattern exists in a DIFFERENT function/file that agent wouldn't naturally encounter
- Agent would need to know "before doing X, look at Y" to find the pattern
- The connection between X and Y isn't obvious from context

**Tripwires vs conventional docs:**

- **Tripwire**: Cross-cutting concerns that apply broadly (e.g., "before using subprocess.run anywhere", "before adding methods to any ABC"). These fire based on action patterns across the codebase.
- **Conventional doc**: Module-specific or localized patterns (e.g., "when implementing session file discovery, check existing patterns in preprocess_session.py"). Add a section to an existing doc or create a focused doc with appropriate `read_when` triggers.

If the pattern is isolated to one module/file, use conventional documentation. Tripwires are for patterns that could occur anywhere.

**Category A (Learning Gaps)** - Would have made the session faster:

- Information that genuinely wasn't in the code (external API quirks, non-obvious interactions)
- Patterns where the "why" isn't clear from reading the code alone
- Gotchas where the code works but has surprising behavior
- Cross-cutting concerns not visible from any single file

**Category B (Teaching Gaps)** - Documentation for what was built:

- New features or commands
- Architectural decisions made
- Conventions established

**IMPORTANT: Teaching gaps require action even when implementation was smooth.**

Unlike learning gaps (which arise from difficulties), teaching gaps exist whenever you BUILD something new. A smooth implementation does NOT mean "no documentation needed."

**Checklist for new features:**

- [ ] New CLI command added? → Update relevant docs (e.g., `docs/learned/cli/`, capability docs)
- [ ] New API/method added to public interface? → Document it
- [ ] New capability added? → Update capability system docs
- [ ] New pattern established? → Document the pattern

**Ask yourself:** "If another agent needs to use or extend what I built, what would they need to know?"

For each item, capture:

- What document to create/update
- Where it belongs (docs/learned/, .claude/skills/, etc.)
- Draft content with specific examples from the session

**If no items pass the filter**, report "No documentation needed - errors were execution discipline issues" and end the session without creating an issue.

### Step 7: Present Findings for Validation

Present your findings to the user with:

1. **Summary of insights** with source attribution:
   - **[Plan]** - From planning/research phase
   - **[Impl]** - From implementation phase

2. **Proposed documentation items** - What you plan to include in the issue

3. **Ask for validation** - Are there insights to add, remove, or refine?

If the user decides to **skip** creating documentation (no valuable insights, or insights already documented), proceed directly to Step 9 to track the evaluation.

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

Write the plan content to a temporary file and get the session ID from the `SESSION_CONTEXT` reminder.

```bash
# Write plan content to a file (example - use actual content)
cat > .erk/scratch/sessions/<session-id>/learn-plan.md << 'EOF'
# Documentation Plan: <title>

## Context

<rich context section here>

## Raw Materials

<gist-url-from-step-4>

## Documentation Items

<items with location, action, draft content, source>
EOF

# Create the learn plan issue
erk exec plan-save-to-issue \
    --plan-type learn \
    --plan-file .erk/scratch/sessions/<session-id>/learn-plan.md \
    --session-id="<session-id-from-SESSION_CONTEXT>" \
    --format display
```

Display the result:

```
Documentation plan created: <issue-url>
Raw materials: <gist-url>
```

### Step 9: Track Learn Evaluation

**CRITICAL: Always run this step**, regardless of whether you created a documentation plan or skipped.

This ensures `erk land` won't warn about unlearned plans:

```bash
erk exec track-learn-evaluation <issue-number> --session-id="<session-id-from-SESSION_CONTEXT>"
```

This posts a tracking comment to the issue to record that learn evaluation was performed.

### Tips

- Preprocessed sessions use XML: `<user>`, `<assistant>`, `<tool_use>`, `<tool_result>`
- `<tool_result>` elements with errors often reveal the most useful insights
- The more context you include in the issue, the faster the implementing agent can work
- Don't be stingy with context - include file contents, code snippets, and reasoning
