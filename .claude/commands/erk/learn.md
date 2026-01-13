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

## Purpose: Token Caches for Agents

**Audience**: All documentation produced by this command is for AI agents, not human users.

**Primary purpose**: These docs are "token caches" - preserved reasoning and research so future agents don't have to recompute it. When you research something, discover a pattern, or figure out how something works, that knowledge should be captured so the next agent doesn't burn tokens rediscovering it.

**Document reality**: Capture the world as it is, not as we wish it to be. "This is non-ideal but here's the current state" is valuable documentation. Tech debt, workarounds, quirks - document them. Future agents need to know how things actually work, not how they should work in an ideal world.

**Bias toward capturing**: When uncertain whether something is worth documenting, include it. Over-documentation is better than losing insights. The cost of re-researching something is higher than the cost of reading an extra paragraph.

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

### Step 2: Analyze What Was Built (MANDATORY)

Before analyzing sessions, understand what code actually changed. This is critical because a smooth implementation with no errors can still add major new capabilities that need documentation.

Get the PR information for this plan:

```bash
# Get PR number from issue (plan issues link to their PR)
gh issue view <issue-number> --json body | jq -r '.body' | grep -o 'PR #[0-9]*' | head -1

# Or find PR by branch pattern
gh pr list --search "head:P<issue-number>-" --json number,title,files
```

Analyze the changes:

```bash
# Get list of changed files with stats
gh pr view <pr-number> --json files,additions,deletions

# Get the actual diff for review
gh pr diff <pr-number>
```

**Create an inventory of what was built:**

- **New files**: What files were created?
- **New functions/classes**: What new APIs were added?
- **New CLI commands**: Any new `@click.command` decorators?
- **New patterns**: Any new architectural patterns established?
- **Config changes**: New settings, capabilities, or options?
- **External integrations**: New API calls, dependencies, or tools?

**Save this inventory** - you will reference it in Step 8 (Teaching Gaps) to ensure everything new gets documented.

### Step 3: Extract Plan Issue Session Content

Attempt to extract session content embedded in the plan issue itself:

```bash
erk exec extract-session-from-issue <issue-number> --stdout
```

This returns the planning session XML that was attached to the issue when it was created (via `erk implement` workflow). This content contains:

- Research and exploration done during planning
- Design decisions and trade-offs considered
- External documentation consulted

**Note:** This may overlap with `planning_session_id` from Step 1, but the issue-embedded content is authoritative. If extraction fails (no embedded content), continue with session logs only.

### Step 4: Check Existing Documentation

Before extracting insights, scan for existing documentation to avoid suggesting duplicates:

```bash
ls -la docs/learned/ 2>/dev/null || echo "No docs/learned/ directory"
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"
```

Create a mental inventory of what's already documented. For each potential insight later, verify it doesn't substantially overlap with existing docs.

### Step 5: Preprocess and Upload Session Content

For each session path from Step 1, preprocess it to compressed XML format and write directly to the destination:

```bash
mkdir -p .erk/scratch/sessions/<current-session-id>/learn

# Preprocess each session directly to destination file using --stdout
# For the planning session:
erk exec preprocess-session <planning-session-path> --max-tokens 15000 --stdout \
    > .erk/scratch/sessions/<current-session-id>/learn/planning-session.xml

# For each implementation session:
erk exec preprocess-session <impl-session-path> --max-tokens 15000 --stdout \
    > .erk/scratch/sessions/<current-session-id>/learn/impl-session-<N>.xml
```

Note: `<current-session-id>` is the session running `/erk:learn`. When `--max-tokens` results in multiple chunks, `--stdout` outputs all chunks with `---CHUNK---` delimiter, which is fine for analysis.

Also save the plan issue session content (from Step 3) if it was retrieved:

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

### Step 6: Deep Session Analysis

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

### Step 7: Identify Learning Gaps

Based on session analysis, identify documentation gaps that would have made the session faster.

**What makes a learning gap:**

- Information that genuinely wasn't in the code (external API quirks, non-obvious interactions)
- Patterns where the "why" isn't clear from reading the code alone
- Gotchas where the code works but has surprising behavior
- Cross-cutting concerns not visible from any single file
- Pattern exists in a DIFFERENT function/file that agent wouldn't naturally encounter
- Agent would need to know "before doing X, look at Y" to find the pattern

**Execution discipline filter (advisory, not strict):**

Some errors are execution discipline issues - the agent should have read the code more carefully. These are LESS likely to be documentation candidates:

- Agent didn't read class/function signature before calling it
- Agent assumed API shape instead of checking type hints
- General language/framework knowledge (pytest patterns, Python stdlib)

However, **when uncertain, include it**. If you're debating whether something is "obvious from the code" vs worth documenting, err toward documenting. The cost of re-researching is higher than the cost of reading an extra paragraph.

**Tripwires vs conventional docs:**

- **Tripwire**: Cross-cutting concerns that apply broadly (e.g., "before using subprocess.run anywhere", "before adding methods to any ABC"). These fire based on action patterns across the codebase.
- **Conventional doc**: Module-specific or localized patterns. Add a section to an existing doc or create a focused doc with appropriate `read_when` triggers.

Record any learning gaps found. **Proceed to Step 8 regardless of whether learning gaps were found.**

### Step 8: Identify Teaching Gaps (MANDATORY)

**This step MUST be executed even if no learning gaps were found.**

Teaching gaps exist whenever you BUILD something new. A smooth implementation does NOT mean "no documentation needed." Unlike learning gaps (which arise from difficulties), teaching gaps arise from creating new capabilities.

**Review your inventory from Step 2.** For EACH item in your inventory, determine what documentation it needs.

**Concrete examples - if you built it, document it:**

| What was built            | Documentation needed                                       |
| ------------------------- | ---------------------------------------------------------- |
| New CLI command           | Document in `docs/learned/cli/` - usage, flags, examples   |
| New gateway method        | Add tripwire about ABC implementation (5 places to update) |
| New capability            | Update capability system docs, add to glossary             |
| New config option         | Add to `docs/learned/glossary.md`                          |
| New exec script           | Document purpose, inputs, outputs                          |
| New architectural pattern | Create architecture doc or add tripwire                    |
| External API integration  | Document quirks, rate limits, auth patterns discovered     |
| New test pattern          | Document in testing docs if others will need it            |

**For each item, ask:** "If another agent needs to use or extend this, what would they need to know?"

**Don't filter based on "obviousness."** Something that seems obvious after you built it required research to figure out. That research is worth caching.

**State of the world documentation is valuable:**

- "This API has a quirk where X happens" - worth documenting
- "We use pattern Y here because of constraint Z" - worth documenting
- "This is non-ideal but works because..." - worth documenting
- Tech debt, workarounds, known limitations - all worth documenting

For each teaching gap item, capture:

- What document to create/update
- Where it belongs (docs/learned/, .claude/skills/, tripwires, etc.)
- Draft content with specific examples from the implementation

**If no learning gaps AND no teaching gaps**, report "No documentation needed" and proceed to Step 11 (track evaluation) without creating an issue. But this should be rare - most implementations that add code also add knowledge worth caching.

### Step 9: Present Findings for Validation

Present your findings to the user with:

1. **Summary of insights** with source attribution:
   - **[Plan]** - From planning/research phase
   - **[Impl]** - From implementation phase

2. **Proposed documentation items** - What you plan to include in the issue

3. **Ask for validation** - Are there insights to add, remove, or refine?

If the user decides to **skip** creating documentation (no valuable insights, or insights already documented), proceed directly to Step 11 to track the evaluation.

### Step 10: Create Documentation Plan Issue

**CRITICAL: Front-load context into the issue.**

Include context you've gathered so the implementing agent doesn't have to rediscover it. This saves tokens and speeds up execution. Include in the issue body:

1. **Rich context section** with:
   - Key files and their purposes (that you discovered)
   - Patterns found in the codebase
   - Relevant existing documentation
   - Any external resources consulted
   - Specific code examples from sessions

2. **Raw materials link** - The gist URL from Step 5

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

<gist-url-from-step-5>

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

### Step 11: Track Learn Evaluation

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
