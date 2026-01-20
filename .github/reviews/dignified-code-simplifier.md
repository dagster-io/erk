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

Check each modified section against the dignified-code-simplifier criteria:

**Code Clarity:**

- Unnecessary complexity and nesting (max 4 levels indentation)
- Redundant code and abstractions
- Variable/function names that could be clearer
- Related logic that could be consolidated
- Unnecessary comments describing obvious code
- Nested ternary operators (prefer if/else or switch for multiple conditions)
- Overly compact code that sacrifices clarity

**Dignified Python Standards:**

- LBYL over EAFP (check conditions proactively)
- Pathlib usage (not os.path)
- Absolute imports only (no relative imports, no re-exports)
- O(1) properties/magic methods (no I/O or iteration)
- Variables declared close to use

**Balance Check:**
Avoid suggesting over-simplification that would:

- Reduce clarity or maintainability
- Create overly clever solutions
- Combine too many concerns
- Remove helpful abstractions
- Make code harder to debug or extend

## Step 4: Inline Comment Format

When posting inline comments for simplification suggestions, use this format:

```
**Code Simplification**: [opportunity type] - [specific suggestion]
```

Example opportunities:

- "Reduce nesting - extract helper function for inner logic"
- "Consolidate logic - these three checks can be combined"
- "Simplify expression - avoid nested ternary, use if/else"
- "Remove redundancy - this variable is used only once"

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
