---
description: Extract learnings from the current session without requiring a plan issue or PR
---

# /local:learn-plan-from-current-session

Capture learnings from the current session. Unlike `/erk:learn`, this command does not require a plan issue, PR, or tracked sessions — it works directly from the current conversation context.

## When to Use

- After exploratory sessions (researching a system, creating objectives, investigating bugs)
- After sessions that didn't produce a PR but generated valuable insights
- When you want to capture learnings immediately while context is fresh

## Agent Instructions

### Step 1: Load Learn Skill

Load the learn skill for anti-dismissal framing and pipeline overview:

```
Skill(skill: "learn")
```

### Step 2: Self-Reflection

**You have direct access to the current session.** This is strictly better than preprocessing JSONL and launching a haiku SessionAnalyzer — you already have full context.

Perform a structured examination of the conversation history:

1. **What was explored?** — List Explore/Task agents launched and their key findings
2. **What external resources were consulted?** — WebFetch/WebSearch URLs and what was learned
3. **What errors were encountered and resolved?** — Error messages, root causes, fixes
4. **What user corrections occurred?** — Where assumptions were wrong
5. **What artifacts were created?** — Files written, commands created, plans saved
6. **What surprised you?** — Non-obvious discoveries, unexpected behaviors

Save the self-reflection to scratch storage:

```bash
mkdir -p .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/
```

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/self-reflection.md",
  content: <structured self-reflection output>
)
```

### Step 3: Optional Session Preprocessing

Check if the current session JSONL exists for subagent analysis:

```bash
find ~/.claude/projects -name "${CLAUDE_SESSION_ID}.jsonl" -type f 2>/dev/null | head -1
```

If found, preprocess it:

```bash
erk exec preprocess-session "<path>" \
    --max-tokens 20000 \
    --output-dir .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn \
    --prefix current
```

This is optional — the self-reflection in Step 2 is the primary source. The preprocessed XML enables SessionAnalyzer to find patterns the parent agent might miss (e.g., subagent logs).

### Step 4: Optional PR Check

Check if the current branch has a PR:

```bash
gh pr view --json number,title 2>/dev/null || echo '{"error": "no PR"}'
```

If a PR exists, save the number for the diff analyzer and PR comment analyzer.

### Step 5: Launch Analysis Agents

Follow the shared reference: `.claude/skills/learn/references/launch-analysis-agents.md`

**Conditional launches:**

- **ExistingDocsChecker**: Always launch. Use self-reflection content to extract search hints.
- **SessionAnalyzer**: Only if preprocessed XML exists from Step 3.
- **CodeDiffAnalyzer**: Only if PR exists from Step 4.
- **PRCommentAnalyzer**: Only if PR exists from Step 4.

For the ExistingDocsChecker, extract the `plan_title` from a summary of the session's main topic (e.g., "Explored objectives system and created multi-plan tracking").

### Step 6: Collect Results

Follow the shared reference: `.claude/skills/learn/references/collect-results.md`

Include the self-reflection file as an additional session analysis path when launching the gap identifier.

### Step 7: Synthesis Pipeline

Follow the shared reference: `.claude/skills/learn/references/synthesis-pipeline.md`

When launching the DocumentationGapIdentifier, include the self-reflection path alongside any session analysis paths:

```
session_analysis_paths: [
  ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/self-reflection.md",
  ... (any session-analyzer outputs)
]
```

For the PlanSynthesizer, set `gist_url` to `"N/A"` (no gist for current-session learning).

### Step 8: Review Plan

Follow the shared reference: `.claude/skills/learn/references/review-plan.md`

### Step 9: Present Findings

Present the synthesized plan inline to the user.

### Step 10: Decision Menu

Present a decision menu:

```
What would you like to do with these findings?
  1. Implement now (Recommended) — Create/update docs in this session
  2. Save as learn plan — Save to GitHub issue for later implementation
  3. Done — Finish without saving
```

**Execute the selected action:**

- **Implement now**: Read the learn plan and create/update the documentation files directly in this session. Use the draft content starters as a starting point. Run CI after making changes.
- **Save as learn plan**: Follow `.claude/skills/learn/references/save-learn-plan.md` (without `--learned-from-issue` flag since there's no parent plan).
- **Done**: End the workflow.
