# Launch Analysis Agents

Launch parallel analysis agents to extract insights concurrently.

## Prerequisites

Before launching agents, ensure:

- Scratch directory exists: `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/`
- Preprocessed session XML files exist (if applicable)
- PR number is known (if applicable)

## Agent Launches

Tell the user:

```
Launching analysis agents in parallel:
  - Session analyzer (1 per session file)
  - Code diff analyzer (PR #<number>) [if PR exists]
  - Existing documentation checker
  - PR comment analyzer (PR #<number>) [if PR exists]
```

### Agent 1: Session Analysis (per session XML)

For each XML file in `.erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/`:

<!-- Model: haiku - Mechanical extraction from XML; deterministic pattern matching -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze session <session-id>",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/session-analyzer.md`

    Input:
    - session_xml_path: .erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn/<filename>.xml
    - context: <brief description from plan title>
)
```

**Skip if**: No preprocessed session XML files exist (e.g., current-session learning with self-reflection only).

### Agent 2: Code Diff Analysis (if PR exists)

<!-- Model: haiku - Structured inventory of changes; no creative reasoning needed -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze PR diff",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/code-diff-analyzer.md`

    Input:
    - pr_number: <pr-number>
    - issue_number: <issue-number>
)
```

**Skip if**: No PR exists for this work.

### Agent 3: Existing Documentation Check

<!-- Model: sonnet - Search and classification; upgraded from haiku to reduce dismissiveness -->

```
Task(
  subagent_type: "general-purpose",
  model: "sonnet",
  run_in_background: true,
  description: "Check existing docs",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/existing-docs-checker.md`

    IMPORTANT: Bias toward capturing documentation. "Self-documenting code" is NOT
    a valid reason to skip documentation. When uncertain, include the item.

    Input:
    - plan_title: <title>
    - pr_title: <PR title if available, or empty string>
    - search_hints: <key terms extracted from title, comma-separated>
)
```

Extract search hints by:

1. Taking significant nouns/concepts from the plan/session title
2. Removing common words (the, a, an, to, for, with, add, update, fix, etc.)
3. Example: "Add parallel agent orchestration" → "parallel, agent, orchestration"

### Agent 4: PR Comment Analysis (if PR exists)

<!-- Model: haiku - Mechanical classification of comments; deterministic pattern matching -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  run_in_background: true,
  description: "Analyze PR comments for docs",
  prompt: |
    Analyze PR review comments to identify documentation opportunities.

    ## Steps
    1. Run: `erk exec get-pr-review-comments --pr <pr-number> --include-resolved`
    2. Run: `erk exec get-pr-discussion-comments --pr <pr-number>`
    3. Classify and summarize the comments

    ## Classification
    For each comment, identify documentation opportunities:
    - **False positives**: Reviewer misunderstood something → document to prevent future confusion
    - **Clarification requests**: "Why does this..." → document the reasoning
    - **Suggested alternatives**: Discussed but rejected → document the decision
    - **Edge case questions**: "What happens if..." → document the behavior

    ## Output Format

    ### PR Comment Analysis Summary
    PR #NNNN: N review threads, M discussion comments analyzed.

    ### Documentation Opportunities from PR Review
    | # | Source | Insight | Documentation Suggestion |
    |---|--------|---------|--------------------------|
    | 1 | Thread at abc.py:42 | Reviewer asked about LBYL pattern | Document when LBYL is required |

    ### Key Insights
    [Bullet list of the most important documentation opportunities]

    If no comments or no documentation opportunities found, output:
    "No documentation opportunities identified from PR review comments."
)
```

**Skip if**: No PR exists for this work.
