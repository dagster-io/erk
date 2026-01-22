# Plan: Add DocumentationGapIdentifier Agent (Step 1B.2)

**Objective:** #5503 - Learn System Improvements (Compound-Inspired)
**Step:** 1B.2 - Add `DocumentationGapIdentifier` agent (determines what needs docs)

## Goal

Create a new agent that synthesizes outputs from the three parallel learn agents (SessionAnalyzer, CodeDiffAnalyzer, ExistingDocsChecker) to produce a prioritized list of documentation gaps. This replaces the manual synthesis logic currently embedded in `/erk:learn`.

## Design Decision: Sequential, Not Parallel

The objective mentions "parallel" but DocumentationGapIdentifier **requires outputs from the other 3 agents**. It cannot run in parallel with them.

**Architecture:**
```
[SessionAnalyzer]     ─┐
[CodeDiffAnalyzer]    ─┼──► [DocumentationGapIdentifier] ──► Gap List
[ExistingDocsChecker] ─┘
```

The gap identifier is a **synthesis agent** - it runs after the parallel agents complete.

## Implementation Phases

### Phase 1: Create Agent Definition

**File:** `.claude/agents/learn/documentation-gap-identifier.md`

```yaml
---
name: documentation-gap-identifier
description: Cross-reference agent findings to identify actual documentation gaps
allowed-tools:
  - Read
  - Glob
  - Grep
---
```

**Input:**
- `session_analysis_paths`: List of session-*.md files in learn-agents/
- `diff_analysis_path`: Path to diff-analysis.md
- `existing_docs_path`: Path to existing-docs-check.md
- `context`: Brief description from plan title

**Responsibilities:**
1. Read all three agent outputs from scratch storage
2. Extract documentation suggestions from session-analyzer and code-diff-analyzer
3. Cross-reference each suggestion against existing-docs-checker findings
4. Classify each suggestion:
   - **ALREADY_DOCUMENTED**: Skip, note existing location
   - **PARTIAL_OVERLAP**: Recommend update vs. new doc
   - **NEW_TOPIC**: Include in gap list
5. Process contradiction warnings (HIGH/MEDIUM/LOW severity)
6. Produce prioritized gap list with rationale

**Output Format:**
```
## Documentation Gap Analysis

### Summary
Total suggestions: <N>
Already documented (skip): <N>
Partial overlap (update): <N>
New topics (gaps): <N>
Contradictions: <N>

### Prioritized Documentation Gaps
| Priority | Topic | Type | Location | Rationale | Source |
|----------|-------|------|----------|-----------|--------|

### Skipped Items (Already Documented)
| Topic | Existing Location | Notes |

### Contradiction Resolution Required
| Topic | Existing Doc | Existing Guidance | New Insight | Severity | Action |

### Partial Overlap Recommendations
| Topic | Existing Doc | What to Add | What Exists |
```

### Phase 2: Update Orchestration in learn.md

**File:** `.claude/commands/erk/learn.md`

**Replace** the manual "Synthesize Agent Findings" section (lines 299-323) with a 4th agent invocation:

```markdown
#### Analyze Documentation Gaps

After writing agent results to scratch storage, launch the gap identifier:

Task(
  subagent_type: "general-purpose",
  run_in_background: false,  # Blocking - we need the result
  description: "Identify documentation gaps",
  prompt: |
    Load and follow `.claude/agents/learn/documentation-gap-identifier.md`
    Input:
    - session_analysis_paths: [list of session-*.md files]
    - diff_analysis_path: .erk/scratch/.../learn-agents/diff-analysis.md
    - existing_docs_path: .erk/scratch/.../learn-agents/existing-docs-check.md
    - context: <plan title>
)

Write output to: .erk/scratch/.../learn-agents/gap-analysis.md
```

**Update** Step 4 ("Identify Documentation Gaps") to read from gap-analysis.md instead of performing manual synthesis.

## Files to Modify

| File | Action |
|------|--------|
| `.claude/agents/learn/documentation-gap-identifier.md` | Create (new agent definition) |
| `.claude/commands/erk/learn.md` | Modify (replace synthesis logic with agent call) |

## Relationship to Other Steps

- **Step 1B.3 (PlanSynthesizer)**: Creates the final learn plan from gap list. Clear separation:
  - GapIdentifier: Determines WHAT needs documentation
  - PlanSynthesizer: Creates HOW to document it (formatted plan)

- **Step 1B.4 (Full orchestration)**: Will wire all 5 agents together with proper dependency ordering

## Verification

1. Run `/erk:learn` on a completed plan with sessions
2. Verify gap-analysis.md is created in scratch storage
3. Verify output contains prioritized gaps with classifications
4. Verify ALREADY_DOCUMENTED items reference existing docs
5. Verify contradictions are flagged with severity

## Related Documentation

- Load `learned-docs` skill if writing documentation
- Existing agents follow pattern in `.claude/agents/learn/`