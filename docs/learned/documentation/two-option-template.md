---
title: Two-Option Documentation Template
read_when:
  - "documenting a decision point with two valid options"
  - "writing docs about when to choose between approaches"
  - "creating comparison documentation"
last_audited: "2026-02-03"
audit_result: edited
---

# Two-Option Documentation Template

Use this template when documenting decisions between two valid approaches. The pattern makes trade-offs explicit and helps agents choose the right option.

## Template

```markdown
# [Feature/Decision Name]

[Brief description of what this is about]

## The Two Options

### Option 1: [Name]

**Pattern:** [Brief workflow description]

[Detailed explanation]

**When to use:**

- [Situation 1]
- [Situation 2]
- [Situation 3]

### Option 2: [Name]

**Pattern:** [Brief workflow description]

[Detailed explanation]

**When to use:**

- [Situation 1]
- [Situation 2]
- [Situation 3]

## Decision Matrix

| Factor        | Option 1 | Option 2 |
| ------------- | -------- | -------- |
| [Criterion 1] | [Value]  | [Value]  |
| [Criterion 2] | [Value]  | [Value]  |
| [Criterion 3] | [Value]  | [Value]  |

## Examples

### Example 1: [Scenario Name]

**Situation:** [Describe the context]

**Decision:** [Which option to choose]

**Reasoning:** [Why this option was right]

## Anti-Patterns

### Don't Do: [Anti-pattern Name]

**Problem:** [What's wrong with this approach]

**Guideline:** [What to do instead]

## Related Documentation

- [Related Doc 1]
- [Related Doc 2]
```

## Real Examples

- [When to Switch Between Planless and Planning](when-to-switch-pattern.md) - Workflow choice

## When to Use This Template

Use when:

- **Two valid approaches exist** — neither is universally better
- **Context determines choice** — different situations favor different options
- **Trade-offs exist** — each option has pros and cons

Don't use when:

- **One option is clearly better** — just document the best practice
- **More than two options** — consider matrix or decision tree format
- **Options aren't alternatives** — they're complementary, not competing

## Related Documentation

- [When to Switch Pattern](when-to-switch-pattern.md) - Example of this template in use
- [Divio Documentation System](divio-documentation-system.md) - Overall doc structure
- [Learned Docs Skill](../../../.claude/skills/learned-docs/SKILL.md) - Documentation authoring patterns
