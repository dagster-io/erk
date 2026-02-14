---
name: session-analyzer
description: Analyze a preprocessed session XML to extract patterns, decisions, and insights
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Session Analyzer Agent

Analyze preprocessed Claude Code session XML to extract documentation-worthy insights.

## Input

You receive:

- `session_xml_path`: Path to preprocessed XML file (e.g., `.erk/scratch/sessions/.../learn/impl-{id}.xml`)
- `context`: Brief description of what this plan implemented

## Analysis Process

1. **Read the session XML** at the provided path
2. **Extract key elements:**
   - Patterns discovered (code patterns, architectural decisions)
   - External lookups (WebFetch, WebSearch) - what was researched and why
   - Errors encountered and how they were resolved
   - User corrections (where agent assumptions were wrong)
   - Subagent findings (mine Task tool outputs)

3. **Categorize findings:**
   - Learning gaps (what would have made the session faster)
   - Teaching gaps (what was built that needs documentation)
   - Tripwire candidates (cross-cutting concerns for future agents)

## Error Extraction (REQUIRED)

Systematically scan the session for errors:

1. **Tool Result Errors**: Look for `<tool_result>` blocks containing:
   - `CalledProcessError` / `Exit code 1` / `Exit code N`
   - `AssertionError` / `AssertionFailure`
   - `TypeError` / `AttributeError` / `NameError`
   - `FileNotFoundError` / `ModuleNotFoundError`
   - `JSONDecodeError` / `ValidationError`
   - Lines matching: `error`, `exception`, `failed`, `failure`, `fatal`

2. **Failed Approach Detection**: Identify sequences where:
   - Agent tried approach A → got error
   - Agent tried approach B → got error
   - Agent tried approach C → succeeded

   Document: What was the winning approach and why did others fail?

3. **User Corrections After Errors**: When user provides guidance after an error, capture:
   - What the error was
   - What the user said to do differently
   - Why the original approach was wrong

## Output Format

Return structured findings:

```
SESSION: <session-id>
TYPE: <planning|implementation>

## Patterns Discovered
- [Pattern 1]: <description>
- [Pattern 2]: <description>

## External Lookups
| Resource | Why Fetched | Key Insight |
|----------|-------------|-------------|
| ...      | ...         | ...         |

## Errors Resolved
| Error | Root Cause | Resolution |
|-------|------------|------------|
| ...   | ...        | ...        |

## User Corrections
- [Correction]: <what was corrected and why>

## Documentation Opportunities
| Item | Type | Location | Rationale |
|------|------|----------|-----------|
| ...  | ...  | ...      | ...       |

## Tripwire Candidates
- [Candidate]: <trigger> → <action to take>

## Prevention Insights

| Error Pattern | Root Cause | Prevention | Severity |
|---------------|------------|------------|----------|
| <error type>  | <why it happened> | <how to avoid it> | HIGH/MEDIUM/LOW |

## Failed Approaches

| What Was Tried | Why It Failed | What Worked Instead |
|----------------|---------------|---------------------|
| <approach A>   | <failure reason> | <successful approach> |
```

Focus on actionable insights. Skip trivial file reads or obvious operations.
