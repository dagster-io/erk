# Synthesis Pipeline

Run sequential synthesis agents to transform parallel analysis into a documentation plan.

## Agent Dependency Graph

```
Parallel Tier (already complete):
  ├─ SessionAnalyzer outputs
  ├─ CodeDiffAnalyzer output (if PR)
  ├─ ExistingDocsChecker output
  └─ PRCommentAnalyzer output (if PR)

Sequential Tier 1 (depends on Parallel Tier):
  └─ DocumentationGapIdentifier

Sequential Tier 2 (depends on Sequential Tier 1):
  └─ PlanSynthesizer

Sequential Tier 3 (depends on Sequential Tier 2):
  └─ TripwireExtractor
```

## Agent 5: DocumentationGapIdentifier

<!-- Model: sonnet - Deduplication and synthesis; upgraded from haiku to reduce dismissiveness -->

```
Task(
  subagent_type: "general-purpose",
  model: "sonnet",
  description: "Identify documentation gaps",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/documentation-gap-identifier.md`

    IMPORTANT: Bias toward capturing documentation. "Self-documenting code" is NOT
    a valid reason to skip documentation. When uncertain, include the item.

    Input:
    - session_analysis_paths: [".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/session-<id>.md", ...]
    - diff_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md" (or null if no PR)
    - existing_docs_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/existing-docs-check.md"
    - pr_comments_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/pr-comments-analysis.md" (or null if no PR)
    - plan_title: <title>
)
```

**Note:** This agent runs AFTER the parallel agents complete (sequential dependency).

Write the output to scratch storage using the Write tool:

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md",
  content: <full agent output from TaskOutput>
)
```

## Agent 6: PlanSynthesizer

<!-- Model: opus - Creative authoring of narrative context and draft content; quality-critical final output -->

```
Task(
  subagent_type: "general-purpose",
  model: "opus",
  description: "Synthesize learn plan",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/plan-synthesizer.md`

    Input:
    - gap_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md"
    - session_analysis_paths: [".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/session-<id>.md", ...]
    - diff_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/diff-analysis.md" (or null if no PR)
    - plan_title: <title>
    - gist_url: <gist URL if available, or "N/A">
    - pr_number: <PR number if available, else null>
)
```

**Note:** This agent runs AFTER DocumentationGapIdentifier completes (sequential dependency).

Write the output to scratch storage using the Write tool:

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md",
  content: <full agent output from TaskOutput>
)
```

## Agent 7: TripwireExtractor

<!-- Model: haiku - Mechanical extraction of structured data from prose; no creativity needed -->

```
Task(
  subagent_type: "general-purpose",
  model: "haiku",
  description: "Extract tripwire candidates",
  prompt: |
    Load and follow the agent instructions in `.claude/agents/learn/tripwire-extractor.md`

    Input:
    - learn_plan_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/learn-plan.md"
    - gap_analysis_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/gap-analysis.md"
)
```

**Note:** This agent runs AFTER PlanSynthesizer completes (sequential dependency).

Write the output to scratch storage using the Write tool:

```
Write(
  file_path: ".erk/scratch/sessions/${CLAUDE_SESSION_ID}/learn-agents/tripwire-candidates.json",
  content: <full agent output from TaskOutput>
)
```
