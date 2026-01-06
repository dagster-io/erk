---
title: Divio Documentation System
read_when:
  - "structuring documentation"
  - "deciding what type of doc to write"
  - "creating tutorials, how-to guides, or reference material"
  - "understanding why docs feel disorganized"
---

# Divio Documentation System

The Divio documentation system (also called "The Grand Unified Theory of Documentation") argues that documentation failures happen because people mix four distinct purposes that require different writing approaches.

**Source**: <https://docs.divio.com/documentation-system/>

## The Four Quadrants

| Type              | Orientation   | Form            | Analogy                     |
| ----------------- | ------------- | --------------- | --------------------------- |
| **Tutorials**     | Learning      | Lesson          | Teaching a child to cook    |
| **How-to Guides** | Goal          | Recipe          | A recipe in a cookbook      |
| **Reference**     | Information   | Dry description | Encyclopedia article        |
| **Explanation**   | Understanding | Discursive      | Article on culinary history |

## The Overlap Problem

Adjacent quadrants share characteristics, which causes docs to "collapse" into mush:

```
              PRACTICAL
                 ↑
    Tutorials ←──┼──→ How-to Guides
         ↑       │       ↑
   STUDYING      │    WORKING
         ↓       │       ↓
   Explanation ←─┼──→ Reference
                 ↓
             THEORETICAL
```

- **Tutorials + How-to**: Both describe practical steps
- **How-to + Reference**: Both needed when coding
- **Reference + Explanation**: Both theoretical knowledge
- **Explanation + Tutorials**: Both for studying, not working

## Tutorials

**Orientation**: Learning-oriented ("learning how", not "learning that")

**Key principle**: You are the teacher. You are responsible for what the learner does.

**Rules**:

- Get the learner started, not to a final destination
- **Must work** - if it produces an error, the tutorial has failed
- Provide immediate visible results for every action
- Minimum explanation - link elsewhere for theory
- Focus on concrete steps, not abstract concepts
- Hand-held baby steps are acceptable

**Test**: Can a complete beginner follow this and succeed?

## How-to Guides

**Orientation**: Goal-oriented (answer "How do I...?" questions)

**Key principle**: Assume some knowledge. The reader knows _what_ they want, not _how_.

**Rules**:

- **Title must work as "How to [title]"** - "How to create a web form" not "Web forms"
- Assume basic knowledge (unlike tutorials)
- Focus on results, not explanation
- Allow flexibility for variations
- Leave things out - usability > completeness
- Practical steps, not theory

**Test**: Does this answer a specific question a user with experience would ask?

## Reference

**Orientation**: Information-oriented

**Key principle**: One job - describe. Structure mirrors codebase.

**Rules**:

- Structure matches the code
- Consistent format (like encyclopedia)
- No instruction, no discussion, no opinion
- Can be partially auto-generated
- Accuracy is paramount - discrepancies lead users astray
- May include usage examples, but not tutorials

**Test**: Is this pure description without instruction or explanation?

## Explanation

**Orientation**: Understanding-oriented

**Key principle**: Provide context, background, and "why". Read "at leisure, away from the code."

**Rules**:

- Can discuss alternatives, opinions, history
- Explains design decisions, historical reasons, constraints
- Provides the bigger picture
- Makes users happier (even if not practically applicable)
- Often scattered or missing in most projects

**Test**: Does this help someone understand _why_, not _how_?

## Applying the Framework

### Diagnosis

When docs feel wrong, check for quadrant collapse:

- Tutorial that stops to explain theory? → Move explanation elsewhere
- Reference that includes step-by-step instructions? → Extract to how-to guide
- How-to guide that teaches basics? → That's a tutorial in disguise

### Writing New Docs

1. **Identify the quadrant first** - What is this doc's ONE job?
2. **Stay in your lane** - Link to other quadrants, don't embed them
3. **Use the right title format**:
   - Tutorial: "Getting Started with X" / "Your First X"
   - How-to: "How to X" (must work grammatically)
   - Reference: Noun phrases matching code ("API Reference", "Configuration Options")
   - Explanation: Topic phrases ("Why X Works This Way", "Understanding X")

## Notable Adopters

- Django (explicit adoption)
- NumPy
- Cloudflare Workers
- Tesla, Bosch, Ericsson (internal)
- PostgREST, Snowpack, BeeWare

## Related Topics

- [Claude.md Best Practices](claude-md-best-practices.md) - Agent-focused documentation patterns
