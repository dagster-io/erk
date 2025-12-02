# Style Guide: Practical Engineering Guides

_For code reviews, best practices, how-to articles_

## Purpose

This guide covers writing actionable, skill-building content for practicing engineers. These pieces teach specific techniques, establish best practices, and help engineers level up their craft. The focus is on immediate applicability and clear value proposition.

## Voice Calibration

### Direct Authority

- Lead with value: "This is the highest leverage activity available to you"
- Use imperatives confidently: "Do this," "Stop doing that," "Start here"
- Quantify impact: "This will save you 10 hours per week"
- Make priorities clear: "This matters more than you think"

### Experience-Backed Wisdom

- Ground advice in repetition: "After reviewing thousands of PRs..."
- Reference scale: "Across 10 years and 3 companies..."
- Share failure stories: "I learned this the hard way when..."
- Acknowledge evolution: "I used to think X, but now..."

### Pragmatic Realism

- Acknowledge when rules don't apply
- Address common objections upfront
- Include escape hatches for special cases
- Respect context and constraints

## Document Structure

### 1. The Value Hook

Start with clear ROI:

```
"Code reviews are the highest leverage activity available
to you as a senior engineer. One hour of good code review
can prevent 10 hours of debugging."
```

### 2. The Credibility Bridge

Establish why they should listen:

```
"I've been on an abnormally accelerated career path at
Facebook, going from E3 to E6 in 3.5 years. Here's what
I learned about what actually matters..."
```

### 3. The Principle List

Core of the guide - numbered, scannable, actionable:

```
## 1. Review the tests first
Always start with the test files. They tell you what the
code is supposed to do without implementation details clouding
your judgment.

**Why this works**: [specific explanation]
**How to do it**: [specific steps]
**Common mistake**: [what to avoid]
```

### 4. The Anti-Patterns

What NOT to do:

```
## What Slows You Down

### The Perfectionist Review
Trying to catch every possible issue will paralyze you...

### The Rubber Stamp
Approving without understanding builds technical debt...
```

### 5. The Implementation Guide

How to start tomorrow:

```
## Your First Week

Day 1: Pick one PR and apply just principle #1
Day 2: Add principle #2 to your workflow
Day 3: Time yourself - aim for 30 minutes max
...
```

### 6. The Reality Check

When to break the rules:

```
## When These Rules Don't Apply

- Emergency hotfixes: Speed over process
- Prototypes: Learning over perfection
- Your first week: Understanding over contributing
```

## Language Patterns

### Action-Oriented Headers

- "How to Review a 1000-Line PR in 30 Minutes"
- "Stop Wasting Time on These 5 Review Anti-Patterns"
- "The One Technique That Transformed My Reviews"

### Specific Over General

Bad: "Review code carefully"
Good: "Read the test file first, then the interface, then implementation"

Bad: "Be thorough"
Good: "Check these 5 things on every PR"

### Quantified Benefits

- "Reduces review time by 50%"
- "Catches 90% of production issues"
- "Takes 5 minutes to learn, saves hours per week"

### Progressive Disclosure

1. State the principle simply
2. Explain why it works
3. Show how to do it
4. Warn about common mistakes
5. Provide advanced variations

## Content Templates

### Best Practices Guide

```markdown
# [Number] Rules for [Specific Activity]

**The Promise**: [What they'll gain]
**The Investment**: [Time/effort required]
**The Credibility**: [Why listen to you]

## Rule 1: [Specific Action]

**The Principle**: [One sentence summary]

**Why This Works**:
[Explanation with example]

**How to Do It**:

1. [Specific step]
2. [Specific step]
3. [Specific step]

**Common Mistake**:
[What people do wrong]

**Advanced Move**:
[For experienced practitioners]

[Repeat for each rule]

## Getting Started

[Incremental adoption plan]

## When to Break These Rules

[Context-specific exceptions]
```

### How-To Article

```markdown
# How to [Specific Goal]

**Time to Learn**: [X minutes]
**Time to Apply**: [Y minutes]
**Impact**: [What improves]

## The Problem

[What's broken now]

## The Solution

[High-level approach]

## Step-by-Step Guide

### Step 1: [Action]

[Detailed instructions with screenshots/code]

### Step 2: [Action]

[Detailed instructions with examples]

## Common Issues

### Issue: [Problem]

Solution: [Fix]

## Next Steps

[Where to go from here]
```

## Practical-Specific Elements

### The Checklist

Make scannable lists for reference:

- [ ] Did you read the tests first?
- [ ] Can you explain the change in one sentence?
- [ ] Did you check for edge cases?
- [ ] Would you deploy this on Friday afternoon?

### The Time Box

Always include time expectations:

- "This should take 30 minutes to read"
- "Apply one principle per day for a week"
- "Speed goal: 20 minutes per review"

### The Graduated Path

Provide progression for different levels:

```
**Beginner**: Focus on rules 1-3
**Intermediate**: Add rules 4-6
**Advanced**: Adapt rules to context
**Expert**: Break rules strategically
```

### Real Code Examples

Show actual before/after:

```python
# Before: What people usually write
def process(data, flag1=False, flag2=False, flag3=False):
    # 50 lines of nested conditionals

# After: What you should write instead
def process(data, config: ProcessConfig):
    # Clear, testable logic
```

## Quality Checklist

- [ ] Opens with clear value proposition
- [ ] Quantifies time investment and ROI
- [ ] Provides numbered, actionable principles
- [ ] Includes anti-patterns to avoid
- [ ] Offers incremental adoption path
- [ ] Acknowledges when rules don't apply
- [ ] Uses specific examples over general advice
- [ ] Can be bookmarked as reference guide

## Examples of Strong Patterns

### The Personal Transformation

"I used to spend 2 hours on every code review. Now I spend 30 minutes and catch more issues. Here's what changed..."

### The Counter-Intuitive Insight

"The best reviewers spend LESS time per PR, not more. They've learned to focus on what matters..."

### The Multiplication Effect

"Teach these principles to your team and multiply your impact by 10x. One senior engineer using these techniques affects every PR in your org..."

### The Failure Story

"I once approved a PR that took down production for 3 hours. It taught me to always check this one thing..."

## What to Avoid

- Vague principles without specific actions
- Advice without explaining the why
- Perfection without acknowledging tradeoffs
- Complex systems without incremental adoption
- Theory without immediate application

## The Practical Guide Formula

Every guide should enable readers to:

1. **Start** applying it immediately
2. **See** results within a week
3. **Measure** the improvement
4. **Adapt** to their context
5. **Teach** others the technique
6. **Know** when not to use it

---

_Next: Select Industry Retrospectives guide for trend analysis_
