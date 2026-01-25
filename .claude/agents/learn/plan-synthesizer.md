---
name: plan-synthesizer
description: Transform gap analysis into a complete, actionable learn plan markdown
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Plan Synthesizer Agent

Transform DocumentationGapIdentifier's structured analysis into a complete, actionable learn plan ready for GitHub issue creation.

## Input

You receive:

- `gap_analysis_path`: Path to DocumentationGapIdentifier output (e.g., `.erk/scratch/sessions/.../learn-agents/gap-analysis.md`)
- `session_analysis_paths`: List of paths to session analysis outputs (for context extraction)
- `diff_analysis_path`: Path to diff analysis output (may be null if no PR exists)
- `plan_title`: Title from the original plan issue
- `gist_url`: URL to raw materials gist
- `pr_number`: PR number if available (for PR comment references)

## Process

### Step 1: Read Gap Analysis

Read the file at `gap_analysis_path` to get:

- Summary statistics
- Contradiction resolutions (HIGH priority)
- Enumerated table of all items
- Prioritized action items
- Tripwire candidates

### Step 2: Extract Rich Context

Read session analysis files to extract:

- What was built (summary of implementation)
- Key decisions made (why certain approaches were taken)
- Challenges overcome (errors, blockers, workarounds)
- Patterns established (new patterns for future reference)
- **Prevention insights** (what went wrong and how to avoid it)

Read diff analysis (if available) to extract:

- Inventory of changes (files, functions, commands added)
- Scope of the implementation

### Step 3: Build Context Narrative

Create a narrative explaining:

1. **What was built**: High-level summary of the implementation
2. **Why documentation matters**: What would a future agent benefit from knowing?
3. **Key insights**: The non-obvious learnings from this implementation

### Step 4: Generate Documentation Items

For each item from the gap analysis (non-SKIP items):

1. **Determine location**: Map to appropriate `docs/learned/` path
2. **Determine action**: CREATE new doc or UPDATE existing
3. **Generate draft content starter**:
   - NOT just "document this" - provide actual starter markdown
   - Include the key points to cover
   - Add source attribution: [Plan], [Impl], or [PR #N]

### Step 5: Describe Tripwire Insights

For items identified as tripwire candidates in the gap analysis, discuss them naturally in the plan:

- **Tripwire Candidates section**: Describe each candidate with its score, the action pattern that should trigger it, the warning message, and the target documentation file. Write this in prose — a separate extraction agent will pull out the structured data.
- **Prevention Insights section**: Describe errors and failed approaches with root cause analysis and prevention recommendations. Note which ones warrant tripwires.
- **Potential Tripwires section**: Items with borderline scores (2-3) that may warrant promotion with additional context.

**Important**: Do NOT use a rigid machine-parseable format like `## Tripwire Additions` with YAML code blocks. A separate tripwire extraction agent handles structured extraction. Write naturally and focus on making the plan readable for humans and implementing agents.

## Output Format

Return a complete learn plan markdown:

````markdown
# Documentation Plan: <plan_title>

## Context

<narrative explaining what was built and why docs matter - 2-3 paragraphs>

## Raw Materials

<gist_url>

## Summary

| Metric                         | Count |
| ------------------------------ | ----- |
| Documentation items            | N     |
| Contradictions to resolve      | N     |
| Tripwire candidates (score≥4)  | N     |
| Potential tripwires (score2-3) | N     |

## Documentation Items

### HIGH Priority

#### 1. <item title>

**Location:** `<path>`
**Action:** CREATE | UPDATE
**Source:** [Plan] | [Impl] | [PR #<N>]

**Draft Content:**

```markdown
<starter markdown for this doc - title, sections, key points to cover>
```
````

---

### MEDIUM Priority

#### 1. <item title>

...

### LOW Priority

#### 1. <item title>

...

## Contradiction Resolutions

<if any contradictions exist>

### 1. <topic>

**Existing doc:** `<path>`
**Conflict:** <description of the contradiction>
**Resolution:** <what to do - update existing, add context, etc.>

## Prevention Insights

Errors and failed approaches discovered during implementation:

### 1. [Error Pattern Name]

**What happened:** <description of the error>
**Root cause:** <why it happened>
**Prevention:** <how to avoid it>
**Recommendation:** TRIPWIRE | ADD_TO_DOC | CONTEXT_ONLY

### 2. ...

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

### 1. <item title>

**Score:** N/10 (criteria: Non-obvious +2, Cross-cutting +2, ...)
**Trigger:** Before <action that should trigger the warning>
**Warning:** <concise warning message>
**Target doc:** `<path to doc where tripwire should be added>`

Describe why this is tripwire-worthy and what harm occurs without it.

## Potential Tripwires

Items with score 2-3 (may warrant promotion with additional context):

### 1. <item title>

**Score:** N/10 (criteria: ...)
**Notes:** <why it didn't meet threshold, what additional evidence would promote it>

```

## Key Principles

1. **Draft content, not placeholders**: Each documentation item should have actual starter markdown, not "TODO: document this"

2. **Source attribution is required**: Every item must indicate whether it came from planning, implementation, or PR review

3. **Context enables execution**: The learn plan should be executable by an agent without access to the original sessions

4. **Prioritization drives order**: HIGH items first (contradictions, gateway methods), then MEDIUM, then LOW

5. **Write tripwire insights naturally**: Describe action patterns, warnings, and target docs in prose. A separate extraction agent handles structured data — do not include `## Tripwire Additions` with YAML code blocks.
```
