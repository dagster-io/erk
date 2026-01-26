---
title: Two-Option Documentation Template
read_when:
  - "documenting a decision point with two valid options"
  - "writing docs about when to choose between approaches"
  - "creating comparison documentation"
---

# Two-Option Documentation Template

Use this template when documenting decisions between two valid approaches. The pattern makes trade-offs explicit and helps agents choose the right option.

## Template Structure

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

| Factor | Option 1 | Option 2 |
|--------|----------|----------|
| [Criterion 1] | [Value] | [Value] |
| [Criterion 2] | [Value] | [Value] |
| [Criterion 3] | [Value] | [Value] |

## Examples

### Example 1: [Scenario Name]

**Situation:** [Describe the context]

**Decision:** [Which option to choose]

**Reasoning:** [Why this option was right]

### Example 2: [Scenario Name]

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

See these docs for examples of this pattern:

- [When to Switch Between Planless and Planning](when-to-switch-pattern.md) - Workflow choice
- [Protocol vs ABC](../architecture/protocol-vs-abc.md) - Type system choice (if exists)

## Key Principles

### 1. Make Trade-Offs Explicit

Don't just describe options. Explain:

- **Costs** - What you give up with each option
- **Benefits** - What you gain with each option
- **Context dependencies** - When costs/benefits matter

### 2. Use Decision Matrix

The table format forces you to identify:

- Objective criteria for comparison
- How options differ on each criterion
- Which criteria matter for the decision

### 3. Provide Concrete Examples

Abstract descriptions confuse. Concrete examples clarify:

- Real scenarios from the codebase
- Actual decisions made
- Why the chosen option was right

### 4. Document Anti-Patterns

Knowing what NOT to do is as valuable as knowing what to do:

- Common mistakes
- Why they fail
- How to avoid them

## When to Use This Template

Use this template when:

- **Two valid approaches exist** - Neither is universally better
- **Context determines choice** - Different situations favor different options
- **Agents need guidance** - Decision is non-obvious
- **Trade-offs exist** - Each option has pros and cons

Don't use this template when:

- **One option is clearly better** - Just document the best practice
- **More than two options** - Consider matrix or decision tree format
- **Options aren't alternatives** - They're complementary, not competing

## Common Decision Points

These topics often fit the two-option pattern:

- **Workflows** - Planless vs Planning, Local vs Remote, etc.
- **Testing approaches** - Integration vs Unit, Mocks vs Fakes
- **Abstractions** - Direct usage vs Gateway, ABC vs Protocol
- **Data structures** - Dataclass vs TypedDict, List vs Generator
- **CLI design** - Subcommand vs Flag, Interactive vs Script mode

## Variations

### Three Options

When there are three options, extend the table:

```markdown
| Factor | Option 1 | Option 2 | Option 3 |
|--------|----------|----------|----------|
```

But consider: Are all three truly alternatives? Often two are closely related and can be combined.

### Decision Tree

For complex decisions with multiple factors, use a decision tree:

```markdown
## Decision Process

1. **Is [criterion 1]?**
   - Yes → Go to Step 2
   - No → Use Option B

2. **Is [criterion 2]?**
   - Yes → Use Option A
   - No → Use Option C
```

### Workflow Comparison

For workflow decisions, show the full process:

```markdown
### Option 1 Workflow

1. Step 1
2. Step 2
3. Step 3

### Option 2 Workflow

1. Step 1
2. Step 2
3. Step 3

**Key difference:** [Highlight where workflows diverge]
```

## Checklist for Quality

Before publishing two-option documentation:

- [ ] Both options are valid (not "right way" vs "wrong way")
- [ ] Decision matrix has objective, measurable criteria
- [ ] At least 2 concrete examples provided
- [ ] Each option has clear "when to use" guidelines
- [ ] Trade-offs are explicit (not just benefits)
- [ ] Anti-patterns documented
- [ ] Links to related documentation included

## Related Documentation

- [When to Switch Pattern](when-to-switch-pattern.md) - Example of this template in use
- [Divio Documentation System](divio-documentation-system.md) - Overall doc structure
- [Learned Docs Guide](../../.claude/skills/learned-docs/learned-docs.md) - Documentation authoring patterns
