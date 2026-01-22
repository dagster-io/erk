# Plan: Add PlanSynthesizer Agent (Objective #5503, Step 1B.3)

## Goal

Create the PlanSynthesizer agent that transforms DocumentationGapIdentifier's structured analysis into a complete, actionable learn plan ready for GitHub issue creation.

## Context

**Current Architecture (4 agents):**
1. SessionAnalyzer (parallel) - extracts patterns from sessions
2. CodeDiffAnalyzer (parallel) - inventories PR changes
3. ExistingDocsChecker (parallel) - finds duplicates/contradictions
4. DocumentationGapIdentifier (sequential) - synthesizes into prioritized gap list

**Gap:** DocumentationGapIdentifier outputs tables and metrics. The learn plan issue needs narrative context and draft content. Currently, the human/AI manually bridges this gap in Step 4-6.

**Solution:** PlanSynthesizer agent transforms gap analysis into complete learn plan markdown.

| Agent | Question Answered | Output |
|-------|-------------------|--------|
| DocumentationGapIdentifier | "What needs docs?" | Tables, metrics, classification |
| PlanSynthesizer | "How do we document it?" | Plan markdown with draft content |

## Implementation

### Phase 1: Create Agent Specification

**File:** `.claude/agents/learn/plan-synthesizer.md`

**Input Contract:**
- `gap_analysis_path`: Path to DocumentationGapIdentifier output
- `session_analysis_paths`: Paths to session analyzer outputs (for context extraction)
- `diff_analysis_path`: Path to diff analyzer output (for inventory context)
- `plan_title`: Title from the original plan issue
- `gist_url`: URL to raw materials gist
- `pr_number`: PR number if available (for PR comment references)

**Processing Steps:**
1. Read gap analysis to get prioritized items
2. Read session/diff outputs to extract rich context
3. For each documentation item:
   - Generate location and action (CREATE/UPDATE)
   - Create draft content starter (not just "document this")
   - Add source attribution ([Plan], [Impl], [PR])
4. Build context narrative explaining what was built
5. Format as learn plan markdown

**Output Format:**
```markdown
# Documentation Plan: <title>

## Context
<narrative about what was built and why docs matter>

## Raw Materials
<gist-url>

## Summary
- Total documentation items: N
- Contradictions to resolve: N
- Tripwires to add: N

## Documentation Items

### HIGH Priority

#### 1. <item title>
**Location:** <path>
**Action:** CREATE | UPDATE
**Source:** [Plan] | [Impl] | [PR #N]

**Draft Content:**
<starter markdown for this doc item>

### MEDIUM Priority
...

### LOW Priority
...

## Tripwire Additions
<formatted tripwire entries ready for frontmatter>
```

**Allowed Tools:** `[Read, Glob, Grep]` (no Bash needed)

### Phase 2: Register Agent in AGENTS.md

Add `plan-synthesizer` to the Task tool's available agent list in the appropriate configuration.

## Files to Modify

| File | Action | Description |
|------|--------|-------------|
| `.claude/agents/learn/plan-synthesizer.md` | CREATE | Agent specification |

## Verification

1. **Unit check:** Agent file follows conventions from existing agents (frontmatter, input/output sections)
2. **Integration check:** Manually test by:
   - Running `/erk:learn` on a completed plan
   - Verifying the agent can be launched via Task tool
   - Checking output matches expected learn plan format

## Related Documentation

- Skills to load: `learned-docs` (for doc location patterns)
- Existing agent patterns: `.claude/agents/learn/documentation-gap-identifier.md`
- Learn skill: `.claude/commands/erk/learn.md` (Step 6 format)

## Out of Scope

- Step 1B.4 (orchestrating all 5 agents) - separate PR
- Modifying `/erk:learn` to use PlanSynthesizer - that's 1B.4