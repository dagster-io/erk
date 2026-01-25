---
title: Skill Composition Patterns
read_when:
  - "creating skills that invoke other skills"
  - "designing skill hierarchies"
  - "understanding skill loading chains"
---

# Skill Composition Patterns

Patterns for creating skills that compose or depend on other skills.

## Two-Layer Skill Composition

Skills can load other skills to leverage domain-specific knowledge:

### Example: PR Push → Diff Analysis → Commit Message

```
/erk:git-pr-push (command)
    └── erk-diff-analysis (skill)
            └── commit-message-prompt (skill)
```

In this chain:

1. `/erk:git-pr-push` command loads `erk-diff-analysis` skill
2. `erk-diff-analysis` skill loads `commit-message-prompt` skill
3. `commit-message-prompt` provides the actual commit message generation guidelines

### Benefits of Composition

| Benefit                | Description                                      |
| ---------------------- | ------------------------------------------------ |
| Reusability            | Inner skill can be used by multiple outer skills |
| Separation of concerns | Each skill focuses on one domain                 |
| Easier testing         | Can test inner skill independently               |
| Reduced duplication    | Common patterns live in one place                |

## Implementation Pattern

### Outer Skill (Consumer)

```markdown
# Outer Skill

This skill handles the overall workflow.

## Prerequisites

Before executing, load the `inner-skill` skill for detailed guidance.

## Workflow

1. Gather context
2. Load `inner-skill` for domain-specific processing
3. Apply results
```

### Inner Skill (Provider)

```markdown
# Inner Skill

Domain-specific guidance for [specific task].

## When to Use

This skill is typically loaded by:

- `outer-skill-1`
- `outer-skill-2`

## Guidelines

[Detailed domain-specific instructions]
```

## Skill Loading Behavior

Skills persist for the entire session once loaded:

- DO NOT reload skills already loaded
- Hook reminders are safety nets, not commands
- Check for `<command-message>The "{name}" skill is loading</command-message>` in conversation

### Loading Check Pattern

Before loading a skill, the system checks if it's already loaded:

```
1. Check conversation history for skill loading message
2. If found, skip loading (skill already active)
3. If not found, load skill
```

## Composition vs Forking

Two approaches to skill composition:

### Composition (Recommended)

Skills reference each other through load instructions:

- Outer skill says "load X for detailed guidance"
- Both skills share conversation context
- Changes to inner skill affect all consumers

### Forking (Advanced)

Using `context: fork` creates isolated execution:

- Forked skill runs in separate context
- Output returned to main conversation
- Use for tasks requiring clean context

See [Context Fork Feature](context-fork-feature.md) for fork details.

## Related Documentation

- [Context Fork Feature](context-fork-feature.md) - Context isolation for skills
- [Agent Commands](agent-commands.md) - Agent command patterns
