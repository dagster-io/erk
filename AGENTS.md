# Erk Coding Standards

> **Note**: This is unreleased, completely private software. We can break backwards
> compatibility completely at will based on preferences of the engineer developing
> the product.

<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority: This is a ROUTING FILE. Load skills and docs as directed for complete guidance. -->

## ⚠️ CRITICAL: Before Writing Any Code

**CRITICAL: NEVER search, read, or access `/Users/schrockn/` directory**

**CRITICAL: NEVER use raw `pip install`. Always use `uv` for package management.**

**CRITICAL: NEVER commit directly to `master`. Always create a feature branch first.**

**Load these skills FIRST:**

- **Python code** → `dignified-python-313` skill (LBYL, modern types, ABC interfaces)
- **Test code** → `fake-driven-testing` skill (5-layer architecture, test placement)
- **Dev tools** → Use `devrun` agent (NOT direct Bash for pytest/pyright/ruff/prettier/make/gt)

## Skill Loading Behavior

**Skills persist for the entire session.** Once loaded, they remain in context.

- **DO NOT reload skills already loaded in this session**
- Hook reminders fire as safety nets, not commands
- If you see a reminder for an already-loaded skill, acknowledge and continue

**Check if loaded**: Look for `<command-message>The "{name}" skill is loading</command-message>` earlier in conversation

## Routing: What to Load Before Writing Code

### Tier 1: Mandatory Skills (ALWAYS Load First)

These fundamentally change how you write code. Load before ANY code work:

| Task                       | Action                            |
| -------------------------- | --------------------------------- |
| Writing Python             | Load `dignified-python-313` skill |
| Writing or modifying tests | Load `fake-driven-testing` skill  |

### Tier 2: Context-Specific Skills

Load when the context applies:

| Context                        | Action                   |
| ------------------------------ | ------------------------ |
| Graphite stacks, `gt` commands | Load `gt-graphite` skill |
| Writing agent documentation    | Load `agent-docs` skill  |

### Tier 3: Tool Routing

Use agents instead of direct Bash:

| Tools                                     | Route                          |
| ----------------------------------------- | ------------------------------ |
| pytest, pyright, ruff, prettier, make, gt | Use `devrun` agent (Task tool) |

### Tier 4: Documentation Lookup

For detailed reference, consult the documentation index which maps each document to specific "read when..." conditions:

→ **[docs/agent/index.md](docs/agent/index.md)** - Complete document registry

**Category quick reference:**

| Category                                 | When to Read                                                               |
| ---------------------------------------- | -------------------------------------------------------------------------- |
| [Architecture](docs/agent/architecture/) | dry-run patterns, Protocol vs ABC, subprocess wrappers, GitHub URL parsing |
| [CLI Development](docs/agent/cli/)       | command organization, output styling, script mode                          |
| [Planning](docs/agent/planning/)         | plan lifecycle, .impl/ folders, agent delegation                           |
| [Testing](docs/agent/testing/)           | erk fakes, rebase conflicts, import conflict resolution                    |
| [Sessions](docs/agent/sessions/)         | session logs, context analysis                                             |
| [Hooks](docs/agent/hooks/)               | hook creation, erk-specific hooks                                          |
| [Kits](docs/agent/kits/)                 | kit CLI commands, kit architecture                                         |
| [Commands](docs/agent/commands/)         | slash command optimization, @ references                                   |
| [Erk](docs/agent/erk/)                   | erk workflows, Graphite branch setup                                       |

**Root documents:**

| Document                                       | When to Read             |
| ---------------------------------------------- | ------------------------ |
| [glossary.md](docs/agent/glossary.md)          | terminology, definitions |
| [conventions.md](docs/agent/conventions.md)    | naming standards         |
| [kit-registry.md](.agent/kits/kit-registry.md) | installed kits           |

## Graphite Stack Quick Reference

- **UPSTACK** = away from trunk (toward leaves/top)
- **DOWNSTACK** = toward trunk (main at BOTTOM)
- **Full details**: Load `gt-graphite` skill for complete visualization and mental model

## Erk-Specific Architecture

Core patterns for this codebase:

- **Dry-run via dependency injection** (not boolean flags)
- **Context regeneration** (after os.chdir or worktree removal)
- **Two-layer subprocess wrappers** (integration vs CLI boundaries)
- **Protocol vs ABC**: Use Protocol for composite interfaces that existing types should satisfy without inheritance; use ABC for interfaces that require explicit implementation

**Protocol vs ABC Decision:**

- **Use Protocol** when you want structural typing (duck typing) - any object with matching attributes works without explicit inheritance. Ideal for composite interfaces like `GtKit` that `ErkContext` already satisfies.
- **Use ABC** when you want nominal typing with explicit inheritance. Ideal for implementation contracts like `Git`, `GitHub`, `Graphite` where you want to enforce that classes explicitly declare they implement the interface.
- **Protocol with `@property`**: When a Protocol needs to accept frozen dataclasses (read-only attributes), use `@property` decorators instead of bare attributes. A read-only consumer accepts both read-only and read-write providers.

**Full guide**: [Architecture](docs/agent/architecture/)

## Project Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **CLI commands**: `kebab-case`
- **Claude artifacts**: `kebab-case` (commands, skills, agents, hooks in `.claude/`)
- **Brand names**: `GitHub` (not Github)

**Claude Artifacts:** All files in `.claude/` (commands, skills, agents, hooks) MUST use `kebab-case`. Use hyphens, NOT underscores. Example: `/my-command` not `/my_command`. Python scripts within artifacts may use `snake_case` (they're code, not artifacts).

**Worktree Terminology:** Use "root worktree" (not "main worktree") to refer to the primary git worktree created with `git init`. This ensures "main" unambiguously refers to the branch name, since trunk branches can be named either "main" or "master". In code, use the `is_root` field to identify the root worktree.

**CLI Command Organization:** Plan verbs are top-level (create, get, implement), worktree verbs are grouped under `erk wt`, stack verbs under `erk stack`. This follows the "plan is dominant noun" principle for ergonomic access to high-frequency operations. See [CLI Development](docs/agent/cli/) for complete decision framework.

## Project Constraints

**No time estimates in plans:**

- 🔴 **FORBIDDEN**: Time estimates (hours, days, weeks)
- 🔴 **FORBIDDEN**: Velocity predictions or completion dates
- 🔴 **FORBIDDEN**: Effort quantification

**Test discipline:**

- 🔴 **FORBIDDEN**: Writing tests for speculative or "maybe later" features
- ✅ **ALLOWED**: TDD workflow (write test → implement feature → refactor)
- 🔴 **MUST**: Only test actively implemented code

## Documentation Hub

- **Full navigation guide**: [docs/agent/guide.md](docs/agent/guide.md)
- **Document index with "read when..." conditions**: [docs/agent/index.md](docs/agent/index.md)
