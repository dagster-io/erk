---
title: Agent Documentation Guide
read_when:
  - "learning how to write agent documentation"
  - "understanding the docs/agent structure"
---

# Agent Documentation Guide

This directory contains documentation specifically written for AI agents working on this codebase.

## Structure

- **Root files** (`glossary.md`, `conventions.md`, etc.): General project knowledge
- **Subdirectories**: Category-specific documentation (architecture, testing, etc.)

## Adding Documentation

1. Create a `.md` file with frontmatter containing `title` and `read_when` fields
2. Run `erk docs sync` to regenerate index files
3. Run `erk docs validate` to check frontmatter

## Frontmatter Format

```yaml
---
title: Document Title
read_when:
  - "condition when agent should read this"
  - "another condition"
tripwires: # Optional
  - action: "before doing X"
    warning: "Do Y instead because Z."
---
```
