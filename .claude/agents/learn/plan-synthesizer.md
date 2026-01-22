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
- Tripwire additions

### Step 2: Extract Rich Context

Read session analysis files to extract:

- What was built (summary of implementation)
- Key decisions made (why certain approaches were taken)
- Challenges overcome (errors, blockers, workarounds)
- Patterns established (new patterns for future reference)

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

### Step 5: Format Tripwire Entries

For each tripwire from gap analysis, format as YAML frontmatter:

```yaml
tripwires:
  - action: "doing X"
    warning: "Do Y instead because Z"
```

## Output Format

Return a complete learn plan markdown:

````markdown
# Documentation Plan: <plan_title>

## Context

<narrative explaining what was built and why docs matter - 2-3 paragraphs>

## Raw Materials

<gist_url>

## Summary

| Metric                    | Count |
| ------------------------- | ----- |
| Documentation items       | N     |
| Contradictions to resolve | N     |
| Tripwires to add          | N     |

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

## Tripwire Additions

Add these to the frontmatter of relevant documents:

### For `<target-doc-path>`

```yaml
tripwires:
  - action: "<trigger action>"
    warning: "<warning message>"
```

```

## Key Principles

1. **Draft content, not placeholders**: Each documentation item should have actual starter markdown, not "TODO: document this"

2. **Source attribution is required**: Every item must indicate whether it came from planning, implementation, or PR review

3. **Context enables execution**: The learn plan should be executable by an agent without access to the original sessions

4. **Prioritization drives order**: HIGH items first (contradictions, gateway methods), then MEDIUM, then LOW

5. **Tripwires are formatted for copy-paste**: YAML blocks should be directly usable in frontmatter
```
