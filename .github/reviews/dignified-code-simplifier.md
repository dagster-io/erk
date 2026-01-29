---
name: Dignified Code Simplifier Review
paths:
  - "**/*.py"
marker: "<!-- dignified-code-simplifier-review -->"
model: claude-haiku-3-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---

## Step 1: Load the Skill

Read the skill file: `.claude/skills/dignified-code-simplifier/SKILL.md`

This skill references `@.claude/skills/dignified-python/` which you should also load.

## Step 2: Apply in Review Mode

Apply the skill's refinement process to the PR diff, but instead of making changes:

- Post inline comments with format: `**Code Simplification**: [what was detected] - [which rule]`
- Focus only on lines starting with `+` in the diff (new/modified code)

## Step 3: Summary Comment

```
### Files Reviewed
- `file.py`: N suggestions
```

Activity log: Keep last 10 entries. Examples: "Found 2 opportunities", "No suggestions", "Dismissed: abstraction provides testability value"
