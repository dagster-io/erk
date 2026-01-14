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

## Purpose

**Audience**: All documentation produced by this command is for AI agents, not human users.

These docs are "token caches" - preserved reasoning and research so future agents don't have to recompute it. When you research something, discover a pattern, or figure out how something works, that knowledge should be captured so the next agent doesn't burn tokens rediscovering it.

**Document reality**: Capture the world as it is, not as we wish it to be. "This is non-ideal but here's the current state" is valuable documentation. Tech debt, workarounds, quirks - document them. Future agents need to know how things actually work.

**Bias toward capturing**: When uncertain whether something is worth documenting, include it. Over-documentation is better than losing insights.

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
- `local_session_ids`: Fallback sessions found locally

If no sessions are found, inform the user and stop.

### Step 2: Analyze Implementation

Before analyzing sessions, understand what code actually changed. A smooth implementation with no errors can still add major new capabilities that need documentation.

Get the PR information for this plan:

```bash
# Get PR number from issue
gh issue view <issue-number> --json body | jq -r '.body' | grep -o 'PR #[0-9]*' | head -1

# Or find PR by branch pattern
gh pr list --search "head:P<issue-number>-" --json number,title,files
```

Analyze the changes:

```bash
gh pr view <pr-number> --json files,additions,deletions
gh pr diff <pr-number>
```

**Create an inventory of what was built:**

- **New files**: What files were created?
- **New functions/classes**: What new APIs were added?
- **New CLI commands**: Any new `@click.command` decorators?
- **New patterns**: Any new architectural patterns established?
- **Config changes**: New settings, capabilities, or options?
- **External integrations**: New API calls, dependencies, or tools?

**Save this inventory** - you will reference it in Step 4 to ensure everything new gets documented.

### Step 3: Gather and Analyze Sessions

#### Check Existing Documentation

Scan for existing documentation to avoid suggesting duplicates:

```bash
ls -la docs/learned/ 2>/dev/null || echo "No docs/learned/ directory"
ls -la .claude/skills/ 2>/dev/null || echo "No .claude/skills/ directory"
```

#### Preprocess Sessions

For each session path from Step 1, preprocess to compressed XML format. Get the current session ID from the `SESSION_CONTEXT` reminder:

```bash
mkdir -p .erk/scratch/sessions/<current-session-id>/learn

# For the planning session:
erk exec preprocess-session <planning-session-path> --max-tokens 15000 --stdout \
    > .erk/scratch/sessions/<current-session-id>/learn/planning-session.xml

# For each implementation session:
erk exec preprocess-session <impl-session-path> --max-tokens 15000 --stdout \
    > .erk/scratch/sessions/<current-session-id>/learn/impl-session-<N>.xml
```

#### Upload to Gist

Upload preprocessed session files to a secret gist:

```bash
gh gist create --desc "Learn materials for plan #<issue-number>" .erk/scratch/sessions/<current-session-id>/learn/*.xml
```

Display the gist URL to the user and save it for the plan issue.

#### Deep Analysis

Read the preprocessed XML files and mine them thoroughly.

**Compaction Awareness:** Long sessions may have been "compacted" (earlier messages summarized), but pre-compaction content still contains valuable research.

**Subagent Mining:**

1. Identify all Task tool invocations (`<invoke name="Task">`)
2. Read subagent outputs - each returns a detailed report
3. Mine Explore agents for codebase findings
4. Mine Plan agents for design decisions
5. Extract specific insights, not just summaries

**What to capture:**

- Files read and what was learned from them
- Patterns discovered in the codebase
- Design decisions and reasoning
- External documentation fetched (WebFetch, WebSearch)
- Error messages and how they were resolved

### Step 4: Identify Documentation Gaps

Based on session analysis and your Step 2 inventory, identify documentation that would help future agents.

#### Learning Gaps

What documentation would have made the session faster?

- Information not in the code (external API quirks, non-obvious interactions)
- Patterns where the "why" isn't clear from reading code alone
- Gotchas where code works but has surprising behavior
- Cross-cutting concerns not visible from any single file

**Execution discipline filter (advisory):** Some errors are execution discipline - agent should have read code more carefully. These are LESS likely to be documentation candidates, but when uncertain, include it.

**Tripwires vs conventional docs:**

- **Tripwire**: Cross-cutting concerns that apply broadly (e.g., "before using subprocess.run anywhere")
- **Conventional doc**: Module-specific or localized patterns

#### Teaching Gaps

**If you built it, document it.** Review your Step 2 inventory. For EACH item, determine documentation needs:

| What was built            | Documentation needed                                       |
| ------------------------- | ---------------------------------------------------------- |
| New CLI command           | Document in `docs/learned/cli/` - usage, flags, examples   |
| New gateway method        | Add tripwire about ABC implementation (5 places to update) |
| New capability            | Update capability system docs, add to glossary             |
| New config option         | Add to `docs/learned/glossary.md`                          |
| New exec script           | Document purpose, inputs, outputs                          |
| New architectural pattern | Create architecture doc or add tripwire                    |
| External API integration  | Document quirks, rate limits, auth patterns discovered     |

For each item, ask: "If another agent needs to use or extend this, what would they need to know?"

**Checkpoint before proceeding:**

- [ ] Did you review EVERY item from your Step 2 inventory?
- [ ] Did you determine documentation needs for each item?
- [ ] If an item needs no documentation, did you explicitly state why?

If no learning gaps AND no teaching gaps, report "No documentation needed" and proceed to Step 7.

### Step 5: Present Findings

Present findings to the user with:

1. **Summary of insights** with source attribution:
   - **[Plan]** - From planning/research phase
   - **[Impl]** - From implementation phase

2. **Proposed documentation items** - What you plan to include in the issue

3. **Ask for validation** - Are there insights to add, remove, or refine?

If the user decides to skip (no valuable insights), proceed to Step 7.

### Step 6: Create Plan Issue

**Front-load context into the issue.** Include:

1. **Rich context section**: Key files, patterns found, relevant existing docs, external resources, code examples
2. **Raw materials link**: The gist URL from Step 3
3. **Documentation items**: Location, action (create/update), draft content, source

Write the plan content and create the issue:

```bash
cat > .erk/scratch/sessions/<session-id>/learn-plan.md << 'EOF'
# Documentation Plan: <title>

## Context

<rich context section>

## Raw Materials

<gist-url>

## Documentation Items

<items with location, action, draft content, source>
EOF

erk exec plan-save-to-issue \
    --plan-type learn \
    --plan-file .erk/scratch/sessions/<session-id>/learn-plan.md \
    --session-id="<session-id>" \
    --format display
```

Display the result:

```
Documentation plan created: <issue-url>
Raw materials: <gist-url>
```

### Step 7: Track Evaluation

**CRITICAL: Always run this step**, regardless of whether you created a plan or skipped.

This ensures `erk land` won't warn about unlearned plans:

```bash
erk exec track-learn-evaluation <issue-number> --session-id="<session-id>"
```

### Tips

- Preprocessed sessions use XML: `<user>`, `<assistant>`, `<tool_use>`, `<tool_result>`
- `<tool_result>` elements with errors often reveal the most useful insights
- The more context you include in the issue, the faster the implementing agent can work
