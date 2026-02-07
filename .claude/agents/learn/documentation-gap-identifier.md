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
- `pr_comments_analysis_path`: Path to PR comment analysis output (may be null if no PR or no comments)
- `plan_title`: Title of the plan being analyzed

## Process

### Step 1: Read All Agent Outputs

Read the files at each provided path:

1. All session analysis files (may be multiple if multiple sessions)
2. Diff analysis file (if provided)
3. Existing docs check file
4. PR comments analysis file (if provided)

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

**From PR Comment Analyzer output (if present):**

- False positives → document to prevent future confusion
- Clarification requests → document the reasoning
- Rejected alternatives → document the decision
- Edge case questions → document the behavior

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
| STALE_DOC          | Mark for DELETE_OR_REWRITE                  |
| HAS_PHANTOM_REFS   | Mark for UPDATE_REFERENCES                  |

### Step 3.5: Adversarial Verification of Contradictions

For each contradiction from ExistingDocsChecker, apply this decision procedure IN ORDER:

1. Check stale reference warnings. If existing doc flagged `STALE_DOC` → reclassify from "contradiction" to `DELETE_STALE_ENTRY`.
2. Two-location skepticism: If two existing docs describe the same concept, check phantom detection data. One stale → delete it. Both clean → genuine inconsistency, recommend `CONSOLIDATE`.
3. Only if neither side has phantom refs → apply standard contradiction resolution.

**"The default is VERIFY, not HARMONIZE."** Never propose "add disambiguation note" without first confirming both systems exist via stale reference data.

### Step 3.7: Ground Truth Verification for Subsystem Claims

Verify that documentation candidates describing subsystems, patterns, or architectural components are grounded in actual code behavior. This step prevents phantom propagation — where docs beget docs without code verification.

**When it fires (mandatory):**

- All `NEW_DOC` candidates tagged `DOC_SOURCED` or `MIXED` (from session analyzer provenance)
- All `NEW_DOC` candidates describing a system, subsystem, pattern, or architectural component
- All candidates where ExistingDocsChecker flagged `HAS_PHANTOM_SUBSYSTEM` or `HAS_STALE_DESCRIPTIONS`

**Verification process for each candidate:**

1. Extract the core claim — what system and what behavior
2. Identify implementation anchors (classes, modules, functions)
3. Search code: `Grep`/`Glob` for anchors in `src/erk/`
4. If anchors found, `Read` the implementation to verify behavioral claims
5. Classify result:

| Result             | Code Evidence                             | Action                                            |
| ------------------ | ----------------------------------------- | ------------------------------------------------- |
| `VERIFIED_IN_CODE` | Implementation matches described behavior | Proceed with NEW_DOC                              |
| `PARTIAL_EVIDENCE` | Some behaviors found, others not          | Narrow scope to verified portions only            |
| `UNVERIFIED_CLAIM` | No code evidence for described system     | **SKIP** — "Subsystem claim not verified in code" |
| `STALE_INHERITED`  | Code exists but does something different  | **SKIP** or rewrite to match actual code behavior |

**Decision rule:** When in doubt, SKIP. A missing doc is less harmful than a wrong doc.

**Provenance escalation:** `DOC_SOURCED` items that fail verification are almost certainly phantom propagation. SKIP with high confidence.

**Key principles:**

- "DOC_SOURCED items need proof" — inherited claims must be verified against code before generating new docs
- "Subsystem descriptions are the riskiest claims" — harder to verify than file paths, more dangerous when wrong

**Cost:** ~10-30 additional tool calls per run (2-5 per candidate, typically 3-10 candidates).

### Step 4: Cross-Reference Against Diff Inventory

Ensure completeness by checking that every item from CodeDiffAnalyzer inventory is accounted for:

- Each new file, function, CLI command, gateway method should have a documentation decision
- If an inventory item has no corresponding documentation candidate, add one

### Step 5: Classify Each Item

Assign a classification to each item:

| Classification    | When to Use                                                 |
| ----------------- | ----------------------------------------------------------- |
| NEW_DOC           | New topic not covered by existing docs                      |
| UPDATE_EXISTING   | Existing doc covers related topic, needs update             |
| UPDATE_REFERENCES | Existing doc valid but has phantom file paths               |
| DELETE_STALE      | Existing doc describes artifacts that no longer exist       |
| TRIPWIRE          | Cross-cutting concern that applies broadly                  |
| SKIP              | Already documented, or doesn't need documentation           |
| SKIP_UNVERIFIED   | Subsystem claim failed ground truth verification (Step 3.7) |

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
| Skipped — unverified (SKIP_UNVERIFIED) | N |
| New documentation needed | N |
| Updates to existing docs | N |
| Tripwire candidates (score >= 4) | N |
| Potential tripwires (score 2-3) | N |
| Contradictions found | N |
| Ground truth verifications performed | N |

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

## Stale Documentation Actions (HIGH Priority)

Existing docs with phantom references requiring cleanup:

| Existing Doc | Phantom References | Action | Rationale |
|---|---|---|---|
| path/to/stale-doc.md | `src/erk/old_module.py` (MISSING) | DELETE_STALE | All referenced artifacts removed |
| path/to/partial-doc.md | `src/erk/renamed.py` (MISSING) | UPDATE_REFERENCES | Core content valid, paths outdated |

## Ground Truth Verification Results

Subsystem claims verified against code in Step 3.7:

| # | Candidate | Provenance | Claim | Anchor | Verification | Action |
|---|-----------|------------|-------|--------|--------------|--------|
| 1 | <item> | DOC_SOURCED | "System X does Y" | `ClassName` in `src/erk/` | VERIFIED_IN_CODE | Proceed |
| 2 | <item> | MIXED | "Module handles Z" | `module_z` in `src/erk/` | PARTIAL_EVIDENCE | Narrow scope |
| 3 | <item> | DOC_SOURCED | "Subsystem manages W" | Not found | UNVERIFIED_CLAIM | SKIP |

## MANDATORY Enumerated Table

Every inventory item MUST appear with a status and rationale:

| # | Item | Type | Status | Provenance | Verification | Location/Action | Rationale |
|---|------|------|--------|------------|--------------|-----------------|-----------|
| 1 | new_function() | function | NEW_DOC | CODE_OBSERVED | VERIFIED_IN_CODE | docs/learned/architecture/foo.md | Establishes new pattern for X |
| 2 | existing_cmd | CLI | UPDATE_EXISTING | MIXED | PARTIAL_EVIDENCE | docs/learned/cli/commands.md | Add new flag documentation |
| 3 | helper_func() | function | SKIP | CODE_OBSERVED | N/A | N/A | Internal helper, no external usage |
| 4 | Gateway.method() | gateway | TRIPWIRE | CODE_OBSERVED | VERIFIED_IN_CODE | tripwires.md | Must update 5 places |
| 5 | phantom_system | subsystem | SKIP_UNVERIFIED | DOC_SOURCED | UNVERIFIED_CLAIM | N/A | Subsystem claim not verified in code |

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

7. **Contradictions are verification opportunities**: First question is "do both reference real code?" not "how to reconcile?"

8. **Two descriptions = staleness signal**: Default assumption is one is stale, not that both are valid.

9. **Delete stale before adding new**: Removing a phantom doc is higher priority than creating a new doc.

10. **DOC_SOURCED items need proof**: Inherited claims must be verified against code before generating new docs. Phantom propagation is the primary failure mode.

11. **Subsystem descriptions are the riskiest claims**: Harder to verify than file paths, more dangerous when wrong. A valid file path does not validate a behavioral claim.
