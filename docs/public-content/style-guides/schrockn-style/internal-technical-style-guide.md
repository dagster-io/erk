# Style Guide: Internal Technical Documentation

_For code smells, architecture decisions, team standards_

## Purpose

This guide covers writing for internal technical audiences—your immediate team and organization. These documents live close to the code, address specific pain points, and create shared standards. Your readers have context about your systems and share your daily struggles.

## Voice Calibration

### Empathetic Authority

- Use collective pronouns: "We violate this rule sometimes"
- Acknowledge shared pain: "We've all seen this pattern"
- Reference shared context: "Remember the outage last quarter"
- Build consensus through inclusion: "Our codebase," "Our team"

### Pragmatic Irreverence

- Use memorable, even provocative descriptions: "Emperor God King Class"
- Make dry concepts stick through personality: "Code that smells"
- Don't be afraid of colorful metaphors within professional bounds
- Let frustration show through in productive ways

### Technically Precise but Accessible

- Assume technical competence but not specific knowledge
- Reference internal systems freely: "Like our `DagsterInstance` problem"
- Use real metrics: "3200 lines," "37 local variables," "10,000s of partition keys"
- Link to specific PRs and commits

## Document Structure

### 1. The Prohibition Hook

Start with a clear, bold directive:

```
## Code Smell: Functions with Invalid Parameter Combinations
**Do not write functions with parameter states that fail at runtime**
```

### 2. The Relatable Pain Point

Immediately connect to shared experience:

- "How many times have you run into code that looks like this and been confused..."
- "We've all seen functions that take 15 parameters where half of them might be None..."
- "Remember when we had that production issue because..."

### 3. The Conceptual Explanation

Why this matters at a systemic level:

- Impact on codebase maintainability
- Effect on developer velocity
- Risk to production systems
- Cognitive load on team members

### 4. The Case Study

Real examples from your codebase:

```
### Case Study: `AssetSubset.size`

Let's look at what's actually happening in our codebase right now.
The `AssetSubset.size` property looks innocent enough:

[code example]

But this triggers a cascade that can fetch from the database
10,000 times for a single property access. Here's the call stack:
[specific trace]

For our customer Discord, this means [specific impact].
```

### 5. The Resolution Tactics

Actionable steps to fix existing problems:

```
### Tactics for Resolution

1. **Immediate mitigation**: Add caching via @cached_property
2. **Medium-term fix**: Refactor to explicit methods
3. **Long-term solution**: Redesign the interface entirely

Here's a PR that shows this transformation: [link]
```

### 6. Prevention Guidelines

How to avoid this in the future:

- Lint rules to add
- Code review checklist items
- Architectural patterns to follow
- Anti-patterns to flag

## Language Patterns

### Inside Baseball is OK

- Reference internal jokes and shared experiences
- Use team-specific terminology without explanation
- Mention specific people: "As Pete discovered..."
- Reference internal discussions: "See our Slack thread about..."

### Show the Actual Pain

- Include real performance numbers
- Show actual stack traces
- Reference specific customer impacts
- Calculate actual costs (time, money, incidents)

### Progressive Disclosure

1. State the problem simply
2. Show a minimal example
3. Reveal the full complexity
4. Trace through actual impact
5. Provide graduated solutions

## Content Templates

### Code Smell Document

```markdown
# Code Smell: [Specific Problem]

**Discussion**: [link to discussion]

## Do not [specific action]

[Relatable opening that connects to shared experience]

### Why This Matters

[Conceptual explanation with technical depth]

### Case Study: [Specific Component]

[Deep dive into actual code with metrics]

### Tactics for Resolution

[Specific, actionable steps]

### Prevention

[Guidelines to avoid recurrence]
```

### Architecture Decision Record

```markdown
# ADR-XXX: [Decision Title]

## Status: [Proposed | Accepted | Deprecated]

## Context

What forced this decision? Include:

- Current pain points with metrics
- Failed attempts to solve this
- Constraints we're operating under

## Decision

What we're doing, specifically

## Consequences

- What gets better
- What gets worse
- What we're betting on

## Alternatives Considered

What else we tried or thought about
```

## Internal-Specific Elements

### Reference Actual Code

```python
# Don't just describe, SHOW:
def problematic_function(
    required: str,
    optional_a: Optional[str] = None,  # Can't be set with optional_b!
    optional_b: Optional[str] = None,  # Can't be set with optional_a!
):
    # 47 lines of spaghetti below...
```

### Link to Everything

- PRs that introduced problems
- PRs that fixed them
- Slack threads discussing them
- Monitoring dashboards showing impact
- Customer tickets affected

### Use Internal Metrics

- "This added 3.7 seconds to our p99 deploy time"
- "We've had 47 instances of this bug in the last quarter"
- "This pattern appears in 23 files across 4 services"

## Quality Checklist

- [ ] Opens with clear prohibition or principle
- [ ] Includes real code from our codebase
- [ ] References specific PRs or commits
- [ ] Quantifies impact with real metrics
- [ ] Provides immediate tactical fixes
- [ ] Suggests long-term strategic improvements
- [ ] Uses "we" and "our" throughout
- [ ] Acknowledges where we've violated this ourselves

## Examples of Strong Openings

### Code Smell

"Do not let classes grow to be too large and assume too many responsibilities. We have a God Class, and its name is `DagsterInstance`. It is a vengeful, dangerous God."

### Architecture Decision

"We're going to break up the `DagsterInstance` class even though it will take 6 months and touch every part of our system. Here's why we can't wait any longer..."

### Best Practice

"Every public API must have runtime parameter checking. We learned this the hard way when a customer passed strings instead of ints and got errors 47 stack frames deep."

## What to Avoid

- Generic advice without specific examples
- Criticism without constructive solutions
- Perfection without acknowledging reality
- External references when internal examples exist
- Prescriptions without explaining tradeoffs

---

_Next: Select External Technical Thought Leadership guide for industry-facing content_
