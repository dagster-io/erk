---
name: documentation-gap-identifier
description: Synthesize outputs from parallel analysis agents to produce prioritized documentation items
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Documentation Gap Identifier Agent

Synthesize outputs from session-analyzer, code-diff-analyzer, and existing-docs-checker agents to produce a prioritized, deduplicated list of documentation items.

## Input

You receive:

- `session_analysis_paths`: List of paths to session analysis outputs (e.g., `learn-agents/session-*.md`)
- `diff_analysis_path`: Path to diff analysis output (may be null if no PR exists)
- `existing_docs_path`: Path to existing docs check output
- `plan_title`: Title of the plan being analyzed

## Process

### Step 1: Read All Agent Outputs

Read the files at each provided path:

1. All session analysis files (may be multiple if multiple sessions)
2. Diff analysis file (if provided)
3. Existing docs check file

### Step 2: Build Unified Candidate List

Extract documentation candidates from all sources:

**From Session Analyzer outputs:**

- Patterns discovered
- Documentation opportunities table entries
- Tripwire candidates
- External lookups (WebFetch/WebSearch) that indicate missing docs
- **Prevention insights** (error patterns and failed approaches)

**From Code Diff Analyzer output (if present):**

- Inventory items (new files, functions, CLI commands, gateway methods)
- Recommended documentation items

**From Existing Docs Checker output:**

- Duplicate warnings (items already documented)
- Contradiction warnings (conflicts to resolve)
- Partial overlap items (may need updates instead of new docs)

### Step 3: Deduplicate Against Existing Documentation

For each candidate, cross-reference against ExistingDocsChecker findings:

| Status             | Action                                      |
| ------------------ | ------------------------------------------- |
| ALREADY_DOCUMENTED | Mark as SKIP with location reference        |
| PARTIAL_OVERLAP    | Mark for UPDATE_EXISTING instead of new doc |
| NEW_TOPIC          | Mark as NEW_DOC candidate                   |

### Step 4: Cross-Reference Against Diff Inventory

Ensure completeness by checking that every item from CodeDiffAnalyzer inventory is accounted for:

- Each new file, function, CLI command, gateway method should have a documentation decision
- If an inventory item has no corresponding documentation candidate, add one

### Step 5: Classify Each Item

Assign a classification to each item:

| Classification  | When to Use                                       |
| --------------- | ------------------------------------------------- |
| NEW_DOC         | New topic not covered by existing docs            |
| UPDATE_EXISTING | Existing doc covers related topic, needs update   |
| TRIPWIRE        | Cross-cutting concern that applies broadly        |
| SKIP            | Already documented, or doesn't need documentation |

### Prevention Item Classification

For items extracted from Prevention Insights and Failed Approaches:

| Severity | Classification             | Example                                                                                  |
| -------- | -------------------------- | ---------------------------------------------------------------------------------------- |
| HIGH     | TRIPWIRE                   | Non-obvious error that affects multiple commands (e.g., missing `--no-interactive` flag) |
| MEDIUM   | NEW_DOC or UPDATE_EXISTING | Error pattern specific to one area (e.g., specific API quirk)                            |
| LOW      | Include in related doc     | Minor gotcha, doesn't need standalone doc                                                |

### Step 6: Score Tripwire Worthiness

For each item classified as TRIPWIRE or prevention insight with HIGH severity, score its tripwire-worthiness.

**Tripwire-Worthiness Criteria:**

| Criterion             | Score | Check                                                       |
| --------------------- | ----- | ----------------------------------------------------------- |
| Non-obvious           | +2    | Error requires context to understand (not clear from code)  |
| Cross-cutting         | +2    | Applies to 2+ commands or multiple areas of the codebase    |
| Destructive potential | +2    | Could cause data loss, invalid state, or significant rework |
| Silent failure        | +2    | No exception thrown; wrong result produced silently         |
| Repeated pattern      | +1    | Same mistake appears 2+ times in sessions                   |
| External tool quirk   | +1    | Involves gh, gt, GitHub API, or other external tool         |

**Scoring Thresholds:**

- Score >= 4 → Mark as `[TRIPWIRE-CANDIDATE]`
- Score 2-3 → Include in "Potential Tripwires" section
- Score < 2 → Regular documentation item

### Step 7: Prioritize by Impact

Assign priority to each item:

| Priority | Criteria                                                                                  |
| -------- | ----------------------------------------------------------------------------------------- |
| HIGH     | Gateway methods (require 5-place updates), contradictions to resolve, external API quirks |
| MEDIUM   | New patterns, CLI commands, architectural decisions                                       |
| LOW      | Internal helpers, minor config changes, pure refactoring                                  |

## Output Format

Return a structured report:

```
# Documentation Gap Analysis

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total candidates collected | N |
| Already documented (SKIP) | N |
| New documentation needed | N |
| Updates to existing docs | N |
| Tripwire candidates (score >= 4) | N |
| Potential tripwires (score 2-3) | N |
| Contradictions found | N |

## Contradiction Resolutions (HIGH Priority)

Resolve these BEFORE creating new documentation:

| Existing Doc | Existing Guidance | New Insight | Resolution |
|--------------|-------------------|-------------|------------|
| path/to/doc.md | "Use pattern A" | "Use pattern B" | UPDATE_EXISTING / CLARIFY_CONTEXT |

For each contradiction:
1. **<topic>**
   - Existing: <path>
   - Conflict: <description>
   - Recommended resolution: <action>

## MANDATORY Enumerated Table

Every inventory item MUST appear with a status and rationale:

| # | Item | Type | Status | Location/Action | Rationale |
|---|------|------|--------|-----------------|-----------|
| 1 | new_function() | function | NEW_DOC | docs/learned/architecture/foo.md | Establishes new pattern for X |
| 2 | existing_cmd | CLI | UPDATE_EXISTING | docs/learned/cli/commands.md | Add new flag documentation |
| 3 | helper_func() | function | SKIP | N/A | Internal helper, no external usage |
| 4 | Gateway.method() | gateway | TRIPWIRE | tripwires.md | Must update 5 places |

## Prioritized Action Items

Sorted by priority (HIGH → MEDIUM → LOW):

### HIGH Priority

1. **<item>** [<classification>]
   - Location: <path>
   - Action: <what to document>
   - Source: <which agent identified this>

### MEDIUM Priority

1. **<item>** [<classification>]
   - Location: <path>
   - Action: <what to document>
   - Source: <which agent identified this>

### LOW Priority

1. **<item>** [<classification>]
   - Location: <path>
   - Action: <what to document>
   - Source: <which agent identified this>

## Skipped Items

Items not requiring documentation:

| Item | Reason | Existing Doc (if applicable) |
|------|--------|------------------------------|
| ... | Already documented | docs/learned/foo.md |
| ... | Internal helper | N/A |
| ... | Pure refactoring | N/A |

## Tripwire Candidates

Items meeting tripwire-worthiness threshold (score >= 4):

| # | Item | Score | Criteria Met | Suggested Trigger |
|---|------|-------|--------------|-------------------|
| 1 | Example: Missing --no-interactive | 6 | Non-obvious, Cross-cutting, Silent failure | "Before calling gt commands without --no-interactive" |

## Potential Tripwires

Items with score 2-3 (may warrant tripwire status with additional context):

| # | Item | Score | Criteria Met | Notes |
|---|------|-------|--------------|-------|
| 1 | ... | 3 | ... | Why it might not meet threshold |

## Tripwire Additions

Cross-cutting concerns to add to docs:

| Trigger Action | Warning | Target Doc |
|----------------|---------|------------|
| "Before using X" | "Do Y instead" | docs/learned/architecture/relevant.md |
```

## Key Principles

1. **Every inventory item must be accounted for**: The enumerated table MUST include every item from the diff analysis inventory

2. **Err toward documentation**: When uncertain whether something needs docs, include it as a candidate

3. **Contradictions are HIGH priority**: Resolve conflicting documentation before adding new docs

4. **Tripwires for cross-cutting concerns**: If a pattern applies broadly (not just one module), suggest a tripwire

5. **Attribution matters**: Track which agent identified each item for traceability

6. **"Self-documenting code" is NOT a valid skip reason**: Code shows WHAT, not WHY. Context, relationships, and gotchas need documentation.
