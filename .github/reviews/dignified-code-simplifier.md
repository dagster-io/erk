---
name: Dignified Code Simplifier Review
paths:
  - "**/*.py"
marker: "<!-- dignified-code-simplifier-review -->"
model: claude-sonnet-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Load the Skill Files

Read these skill files from the repository:

1. .claude/skills/dignified-code-simplifier/SKILL.md (main skill definition)
2. .claude/skills/dignified-python/SKILL.md (referenced dignified-python standards)
3. .claude/skills/dignified-python/dignified-python-core.md (LBYL, exceptions, paths, imports, DI, performance)

## Step 2: Identify Changed Python Code

For each Python file in the PR diff, determine which lines were actually modified:

- Lines starting with `+` in the diff are additions/modifications
- Lines starting with ` ` (space) are unchanged context

Focus only on changed code, not context lines.

## Step 3: Analyze for Simplification Opportunities

Apply the criteria from the skill files loaded in Step 1. The dignified-code-simplifier skill defines what to look for (code clarity, dignified-python standards, balance checks).

## Step 4: Inline Comment Format

When posting inline comments for simplification suggestions, use this format:

```
**Code Simplification**: [opportunity type] - [specific suggestion]
```

Examples: "Reduce nesting - extract helper", "Consolidate logic - combine checks", "Remove redundancy - variable used once"

## Step 5: Summary Comment Format

Summary format (preserve existing Activity Log entries and prepend new entry):

```
### Files Reviewed
- `file.py`: N suggestions
```

Activity log entry examples:

- "Found 2 opportunities (reduce nesting in x.py, consolidate logic in y.py)"
- "No simplification opportunities found"
- "Suggestion dismissed: abstraction provides value for testability"

Keep the last 10 log entries maximum.
