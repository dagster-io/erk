---
title: CLAUDE.md and AGENTS.md Best Practices
read_when:
  - "writing or updating CLAUDE.md or AGENTS.md files"
  - "creating project documentation for AI agents"
  - "setting up new agent-driven projects"
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

**Pattern:**

```markdown
## Routing: What to Load Before Writing Code

- **Writing Python** → Load `dignified-python` skill
- **Writing tests** → Load `fake-driven-testing` skill
- **Worktree operations** → Load `gt-graphite` skill

**Full documentation**: See [docs/learned/index.md](docs/learned/index.md)
```

**Benefits:**

- Keeps CLAUDE.md/AGENTS.md under token budget
- Allows detailed guidance to live in skills and docs
- Creates clear mental model of "routing file" vs "reference docs"

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

Use HTML comments to provide meta-instructions about the file itself:

```markdown
<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority: This is a ROUTING FILE. Load skills and docs as directed for complete guidance. -->
```

**Why HTML comments?**

- Not rendered in markdown viewers
- Creates clear distinction between meta-instructions and content
- Stands out visually when Claude reads the file

### Behavioral Triggers

Use trigger patterns to route Claude to documentation at the right moment:

```markdown
**CRITICAL: Before passing dry_run boolean flags through function parameters**
→ Read [Erk Architecture Patterns](architecture/erk-architecture.md) first.
```

**Pattern:**

- Start with trigger condition ("Before X...")
- Point to specific documentation
- Often includes rationale or consequence

### Cross-References

Use consistent notation for linking to related content:

```markdown
@docs/learned/tripwires.md
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
- **Tier-based Routing**: Mandatory → Context-Specific → Tool Routing → Documentation
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
  - "action pattern that should load this doc"
---
```

**Indexing**: The `erk docs sync` command auto-generates `docs/learned/index.md` from these frontmatter blocks.

### Progressive Disclosure Tiers

**Tier 1: Mandatory Skills** (always load first)

- Fundamentally change how you write code
- Examples: `dignified-python`, `fake-driven-testing`

**Tier 2: Context-Specific Skills** (load when context applies)

- Domain-specific guidance
- Examples: `gt-graphite`, `learned-docs`

**Tier 3: Tool Routing** (use agents instead of direct commands)

- Delegation patterns
- Example: Use `devrun` agent for pytest/pyright/ruff

**Tier 4: Documentation Lookup** (reference when needed)

- Detailed guides and patterns
- Accessed via index: `docs/learned/index.md`

## Examples

### Good Preamble Pattern

```markdown
# MyProject - Real-Time Analytics Platform

## What is MyProject?

**MyProject** is a real-time analytics platform for processing streaming data.

**Status**: Production system serving 100K+ users daily.

## Core Architecture

**Tech Stack:**

- Python 3.11+ (FastAPI, SQLAlchemy)
- PostgreSQL + Redis
- Docker + Kubernetes

**Design Principles:**

- Event-driven architecture
- Immutable data patterns
- Zero-downtime deployments

## How Agents Work on This Project

**Routing Model**: This file directs you to load skills and docs based on task.

**Key Skills:**

- `backend-patterns`: API design, database migrations
- `testing-patterns`: Integration test setup

**Documentation**: See [docs/index.md](docs/index.md)
```

**Why this works:**

- Concise (~30 lines)
- Clear WHAT/WHY/HOW structure
- Links to detailed docs
- Universally applicable

### Bad Preamble Pattern

```markdown
# MyProject

This is a really great project that does analytics. We use Python and FastAPI.

When you're implementing authentication, make sure to use JWT tokens with RS256
signing. Store the private key in environment variables. Add rate limiting to
all endpoints using the RateLimiter class in src/middleware.py.

For database queries, always use SQLAlchemy ORM. Never write raw SQL. Add
indexes to any columns you query frequently. Make sure to handle connection
pooling properly.

Follow PEP 8 style guide. Use black for formatting. Sort imports with isort.
Add type hints to all functions. Write docstrings in Google style.

[continues for 500 lines...]
```

**Why this fails:**

- No clear structure
- Mixes task-specific guidance with universal rules
- Includes linter rules (should be in configs)
- Way too long (degrades instruction-following)
- No progressive disclosure

## Sources

This guidance synthesizes best practices from:

- **[Claude Code: Best practices for agentic coding](https://www.anthropic.com/engineering/claude-code-best-practices)** — Anthropic's official best practices for Claude Code, including WHAT/WHY/HOW structure and token budget constraints.

- **[Writing a good CLAUDE.md | HumanLayer Blog](https://www.humanlayer.dev/blog/writing-a-good-claude-md)** — Practical patterns for effective CLAUDE.md files, focusing on universal applicability and progressive disclosure.

- **[Using CLAUDE.MD files: Customizing Claude Code for your codebase | Claude](https://claude.com/blog/using-claude-md-files)** — Official Claude blog post explaining CLAUDE.md purpose and common patterns.

- **[Skill authoring best practices - Claude Docs](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)** — Guidance on creating effective skills that complement CLAUDE.md/AGENTS.md files.
