---
name: existing-docs-checker
description: Search existing documentation to identify duplicates and contradictions before suggesting new docs
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Existing Docs Checker Agent

Search `docs/learned/`, `.claude/commands/`, and `.claude/skills/` to identify what documentation already exists before suggesting duplicates during learn extraction. Also detect potential contradictions between existing docs and new insights.

## Input

You receive:

- `plan_title`: Title of the plan being analyzed (e.g., "Add parallel agent orchestration")
- `pr_title`: PR title if available (often similar to plan title)
- `search_hints`: Key terms extracted from plan title (e.g., "parallel", "agent", "orchestration")

## Search Process

1. **Generate search terms from inputs:**
   - Extract key nouns and concepts from plan_title
   - Combine with provided search_hints
   - Remove common words (the, a, an, to, for, with, etc.)

2. **Search documentation directories:**

   Search across all three documentation locations:
   - `docs/learned/` - Agent-generated documentation
   - `.claude/commands/` - Claude Code slash commands
   - `.claude/skills/` - Claude Code skills

   For each search term:

   ```
   Grep(pattern: "<term>", path: "docs/learned/")
   Grep(pattern: "<term>", path: ".claude/commands/")
   Grep(pattern: "<term>", path: ".claude/skills/")
   ```

3. **Read relevant files:**
   - For files with multiple matches, read and summarize content
   - Extract frontmatter `title` and `read_when` fields
   - Note what topics each file covers

4. **Classify findings:**
   - **Direct match**: Existing doc covers this exact topic
   - **Partial overlap**: Existing doc covers related topic
   - **No match**: Topic not currently documented

5. **Detect contradictions:**
   When reading related files, look for statements that conflict with the new insights being documented:
   - **Opposite guidance**: Doc A says "do X", new insight says "don't do X"
   - **Outdated patterns**: Existing doc recommends deprecated approach
   - **Conflicting constraints**: Different docs give incompatible rules for same scenario
   - **Version drift**: Doc references old API/syntax that's been superseded

   Common contradiction patterns:
   - "Use try/except" vs "Use LBYL (check first)"
   - "Required" vs "Optional" for same tool/feature
   - "Always" vs "Never" for same action
   - Different file paths or command syntax for same operation

## Output Format

Return structured findings:

```
## Existing Documentation Search

### Summary
Plan title: <plan_title>
Search terms used: <list of terms>
Total files searched: <N>
Files with matches: <N>
Potential duplicates: <N>
Potential contradictions: <N>

### Search Results

| Search Term | Matches Found | Files |
|-------------|---------------|-------|
| ...         | ...           | ...   |

### Existing Documentation Found

| File | Title | Covers | Relevance |
|------|-------|--------|-----------|
| docs/learned/architecture/parallel-agent-pattern.md | Parallel Agent Orchestration Pattern | Agent parallelism | High |
| ...  | ...   | ...    | Low/Medium/High |

### Recommendations

For each topic that might be documented:

1. **<topic>**
   - Status: ALREADY_DOCUMENTED | PARTIAL_OVERLAP | NEW_TOPIC
   - Existing doc: <path or "none">
   - Recommendation: <what to do>

### Duplicate Warnings

If suggesting new documentation, these topics already have coverage:
- <topic>: See <existing-doc-path>

### Contradiction Warnings

Potential conflicts between existing docs and new insights:

| Existing Doc | States | New Insight States | Severity |
|--------------|--------|-------------------|----------|
| docs/learned/architecture/foo.md | "Use pattern A" | "Use pattern B" | HIGH |
| .claude/skills/bar.md | "X is required" | "X is optional" | MEDIUM |

For each contradiction:

1. **<topic>**
   - Existing doc: <path>
   - Existing guidance: "<quote or summary>"
   - New insight: "<conflicting statement>"
   - Severity: HIGH | MEDIUM | LOW
   - Resolution: UPDATE_EXISTING | CLARIFY_CONTEXT | INVESTIGATE
```

## Key Principles

### Duplicate Detection

- **Err toward flagging duplicates**: Better to flag a false positive than miss a duplicate
- **Check frontmatter**: The `read_when` field often reveals if a doc covers a topic
- **Consider skill documents**: Skills like `fake-driven-testing` contain substantial documentation
- **Check commands too**: Some documentation lives in command files (e.g., `/erk:learn` documents the learn workflow)

### Contradiction Detection

- **Err toward flagging contradictions**: Surface potential conflicts for human review
- **Context matters**: "Use X" in one context and "Don't use X" in another may not be contradictory
- **Check tripwires.md**: Tripwires contain authoritative "CRITICAL" rules—contradicting these is HIGH severity
- **Newer isn't always right**: The new insight may be wrong; flag for investigation, don't assume
- **Look for absolutes**: Words like "always", "never", "required", "forbidden" signal strong claims that may conflict
