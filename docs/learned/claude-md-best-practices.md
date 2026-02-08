---
title: CLAUDE.md and AGENTS.md Best Practices
read_when:
  - "writing or updating CLAUDE.md or AGENTS.md files"
  - "creating project documentation for AI agents"
  - "setting up new agent-driven projects"
last_audited: "2026-02-05 20:38 PT"
audit_result: edited
---

# CLAUDE.md and AGENTS.md Best Practices

## Overview

**CLAUDE.md** and **AGENTS.md** are special markdown files that customize how Claude Code works on your codebase. They act as persistent instructions that load automatically into every session.

**Purpose:**

- **CLAUDE.md**: User-specific global instructions (stored in `~/.claude/`)
- **AGENTS.md**: Project-specific instructions (checked into repository)
- Both files guide Claude's behavior, coding standards, and workflow patterns

**Key Insight**: These files are not comprehensive references—they are **routing documents** that direct Claude to load the right skills and documentation based on the current task.

## Best Practices Framework

### WHAT/WHY/HOW Structure

Effective preambles follow this pattern:

1. **WHAT**: Tech stack, structure, architecture
   - Programming languages and versions
   - Key frameworks and tools
   - Project organization and directory structure
   - Core architectural patterns

2. **WHY**: Purpose, goals, constraints
   - What problem does this project solve?
   - Who uses it and how?
   - Key design principles and philosophies
   - Important constraints or requirements

3. **HOW**: Build tools, testing, verification
   - Common commands and workflows
   - How to run tests and verify changes
   - Development environment setup
   - CI/CD integration patterns

### Keep It Minimal

**Token Budget Reality:**

- Frontier LLMs can follow ~150-200 instructions with reasonable consistency
- Claude Code's system prompt already contains ~50 instructions
- This leaves room for ~100-150 instructions in CLAUDE.md/AGENTS.md

**Target Length:**

- **Sweet spot**: 100-200 lines total
- **Maximum**: 300 lines (beyond this, instruction-following degrades)
- **Preamble**: 40-60 lines (leaves room for routing rules)

### Universal Applicability

**Golden Rule**: Only include information relevant to **every session**.

**Good examples** (universally applicable):

- "Always use `uv` for package management, never `pip install`"
- "Run `make test` before committing"
- "Never commit directly to `master`—create feature branches"

**Bad examples** (task-specific):

- "When implementing authentication, use JWT tokens"
- "Add error handling to all API endpoints"
- "Follow REST conventions for endpoint naming"

**Why this matters**: Task-specific guidance causes Claude to ignore the entire file, treating it as noise rather than persistent instructions.

### Progressive Disclosure

**Core Principle**: Link to detailed docs instead of stuffing everything inline.

Use a routing table that maps task types to skills or docs (see the "Load these skills FIRST" section in AGENTS.md for a live example). This keeps the main file under token budget while allowing detailed guidance to live in skills and documentation files.

## Critical Constraints

### Length Limits

**What happens when files get too long:**

- Instruction-following degrades (Claude starts ignoring rules)
- Token budget waste (every session pays the cost)
- Maintenance burden (harder to keep current)

**Avoid including:**

- ❌ Code style guidelines (use linter configs instead)
- ❌ Exhaustive command lists (link to docs instead)
- ❌ Detailed API documentation (belongs in code comments)
- ❌ Implementation patterns for specific features

**Do include:**

- ✅ Commands you type repeatedly
- ✅ Architectural context (WHAT/WHY/HOW)
- ✅ Workflows that prevent rework
- ✅ Critical safety rules (e.g., "never delete production data")

### What to Document

**High-value content:**

- Common bash commands with descriptions
- Core files and utility functions
- Testing instructions and verification steps
- Repository conventions (branching, merge strategies)
- Developer environment setup requirements
- Project-specific quirks or warnings
- Institutional knowledge you want preserved

**Low-value content** (omit or link instead):

- Generic coding advice
- Language syntax references
- Framework documentation
- Style preferences (let linters handle this)

## Structural Strategies

### HTML Comments as Signals

Use HTML comments for meta-instructions about the file itself (see the top of AGENTS.md for a live example: `AGENT NOTICE` and `BEHAVIORAL TRIGGERS` comments). HTML comments are not rendered in markdown viewers, creating a clear distinction between instructions about the file and the file's content.

### Behavioral Triggers

Use trigger patterns to route Claude to documentation at the right moment. The pattern is: start with a trigger condition ("CRITICAL: Before X..."), then point to specific documentation. See the "CRITICAL" lines in AGENTS.md for live examples. This ensures guidance is loaded just-in-time rather than cluttering every session.

### Cross-References

Use consistent notation for linking to related content:

```markdown
@docs/learned/cli/tripwires.md
```

**Benefits:**

- Creates trackable references
- Signals "this is a link to load"
- Maintains consistency across files

## Erk-Specific Patterns

### Routing File Philosophy

**AGENTS.md** in this project implements a "routing document" pattern:

1. **Preamble** (~40 lines): WHAT/WHY/HOW project overview
2. **Routing Rules** (~100 lines): When to load which skills/docs
3. **Quick Reference** (~50 lines): High-frequency patterns and constraints

**Key sections:**

- **Skill Loading Behavior**: When and how to load skills
- **Documentation-First Discovery**: Grep docs/learned/ before coding
- **Critical Constraints**: Absolute rules (FORBIDDEN/ALLOWED patterns)

### YAML Frontmatter Pattern

Documentation files in `docs/learned/` use YAML frontmatter for metadata:

```yaml
---
title: Document Title
read_when:
  - "condition that triggers reading this doc"
  - "another condition"
tripwires:
  - action: "action pattern that should load"
    warning: "action pattern that should load this doc"
  - action: "performing actions related to this tripwire"
    warning: "--"
```

**Indexing**: The `erk docs sync` command auto-generates `docs/learned/index.md` from these frontmatter blocks.

### Progressive Disclosure Tiers

A useful mental model for organizing content across skill and documentation layers:

1. **Mandatory skills** (always load first): Fundamentally change how you write code (e.g., `dignified-python`, `fake-driven-testing`)
2. **Context-specific skills** (load when context applies): Domain-specific guidance (e.g., `gt-graphite`, `learned-docs`)
3. **Tool routing** (use agents instead of direct commands): Delegation patterns (e.g., `devrun` agent for pytest/ty/ruff)
4. **Documentation lookup** (reference when needed): Detailed guides accessed via `docs/learned/index.md`

## Examples

### Good vs. Bad Preamble Patterns

**Good preamble** (~30 lines): Concise WHAT/WHY/HOW structure, links to detailed docs, universally applicable. See AGENTS.md in this project for a live example: it opens with project description, lists tech stack, then routes to skills and documentation.

**Bad preamble** (500+ lines): Mixes task-specific guidance with universal rules ("when implementing authentication, use JWT tokens..."), duplicates linter configs, includes framework documentation inline. Causes instruction-following degradation because Claude treats the entire file as noise.

## Sources

This guidance synthesizes best practices from:

- **[Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)** — Anthropic's official best practices for Claude Code, including WHAT/WHY/HOW structure and token budget constraints.

- **[Writing a good CLAUDE.md | HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)** — Practical patterns for effective CLAUDE.md files, focusing on universal applicability and progressive disclosure.

- **[Using CLAUDE.MD files: Customizing Claude Code for your codebase | Claude](https://claude.com/blog/using-claude-md-files)** — Official Claude blog post explaining CLAUDE.md purpose and common patterns.

- **[Skill authoring best practices - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)** — Guidance on creating effective skills that complement CLAUDE.md/AGENTS.md files.
