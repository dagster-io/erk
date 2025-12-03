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

## Quick Routing Table

| If you're about to...                            | STOP! Check this instead                                      |
| ------------------------------------------------ | ------------------------------------------------------------- |
| Write Python code                                | → Load `dignified-python-313` skill FIRST                     |
| Write or modify tests                            | → Load `fake-driven-testing` skill FIRST                      |
| Run pytest, pyright, ruff, prettier, make, or gt | → Use `devrun` agent (Task tool), NOT Bash                    |
| Work with Graphite stacks                        | → Load `gt-graphite` skill                                    |
| Use dry-run, subprocess wrappers, Protocol/ABC   | → [Architecture](docs/agent/architecture/)                    |
| Style output, organize commands, script mode     | → [CLI Development](docs/agent/cli/)                          |
| Create plans, .impl/ folders, delegate to agents | → [Planning](docs/agent/planning/)                            |
| Use erk fakes, fix rebase conflicts in tests     | → [Testing](docs/agent/testing/)                              |
| Find session logs, debug context window          | → [Sessions](docs/agent/sessions/)                            |
| Create hooks, erk-specific reminders             | → [Hooks](docs/agent/hooks/)                                  |
| Build kit CLI commands, kit code structure       | → [Kits](docs/agent/kits/)                                    |
| Reduce command size, use @ references            | → [Commands](docs/agent/commands/)                            |
| Write or edit agent documentation                | → Load `agent-docs` skill FIRST                               |
| Look up terminology or conventions               | → [glossary.md](docs/agent/glossary.md)                       |
| Navigate documentation                           | → [guide.md](docs/agent/guide.md)                             |
| View installed kits                              | → [@.agent/kits/kit-registry.md](.agent/kits/kit-registry.md) |

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

- **Navigation**: [docs/agent/guide.md](docs/agent/guide.md)
- **Installed kits**: [@.agent/kits/kit-registry.md](.agent/kits/kit-registry.md)
- **Python standards**: Load `dignified-python-313` skill
- **Test architecture**: Load `fake-driven-testing` skill
- **Graphite stacks**: Load `gt-graphite` skill
