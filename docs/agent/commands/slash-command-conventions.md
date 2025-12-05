---
title: Slash Command Conventions
read_when:
  - "writing or modifying slash commands"
  - "creating command documentation"
  - "organizing command structure"
---

# Slash Command Conventions

This document defines conventions for writing and maintaining slash commands.

## Step Numbering in Slash Commands

**Rule**: Always use whole-number steps in slash command documentation.

### Correct

```markdown
### Step 1: Do first thing

### Step 2: Do second thing

### Step 3: Do third thing
```

### Incorrect

```markdown
### Step 1: Do first thing

### Step 1.5: Do inserted thing # ❌ Don't use fractional steps

### Step 2: Do second thing
```

### Why

- Fractional steps (1.5, 2.5) indicate steps were inserted without renumbering
- Makes commands harder to reference ("run step 3" vs "run step 2.5")
- Creates maintenance burden when steps need to be added/removed
- When adding steps, renumber all subsequent steps to maintain whole numbers

### Refactoring Fractional Steps

When you encounter fractional step numbers:

1. Renumber all steps to use whole numbers
2. Update any references to step numbers in the text
3. Consider whether the "inserted" step indicates missing structure

Example refactoring:

Before:

```markdown
### Step 1: Validate environment

### Step 2: Read plan file

### Step 2.5: Load related documentation

### Step 3: Create todo list
```

After:

```markdown
### Step 1: Validate environment

### Step 2: Read plan file

### Step 3: Load related documentation

### Step 4: Create todo list
```

## Related Topics

- [Command Optimization Patterns](optimization-patterns.md) - Reducing command size with @ references
- [Behavioral Triggers](behavioral-triggers.md) - Using routing patterns in commands
