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
```

Focus on actionable insights. Skip trivial file reads or obvious operations.
