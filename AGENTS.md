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

| If you're about to...                            | STOP! Check this instead                                                               |
| ------------------------------------------------ | -------------------------------------------------------------------------------------- |
| Write Python code                                | → Load `dignified-python-313` skill FIRST                                              |
| Write or modify tests                            | → Load `fake-driven-testing` skill FIRST                                               |
| Run pytest, pyright, ruff, prettier, make, or gt | → Use `devrun` agent (Task tool), NOT Bash                                             |
| Import time or use time.sleep()                  | → Use `context.time.sleep()` instead (see erk-architecture.md#time-abstraction)        |
| Work with Graphite stacks                        | → Load `gt-graphite` skill for stack visualization and terminology                     |
| Understand erk architecture patterns             | → [docs/agent/erk-architecture.md](docs/agent/erk-architecture.md)                     |
| Design interface (Protocol vs ABC)               | → [docs/agent/protocol-vs-abc.md](docs/agent/protocol-vs-abc.md)                       |
| Use planning workflow (.impl/ folders)           | → [docs/agent/planning-workflow.md](docs/agent/planning-workflow.md)                   |
| Understand full plan lifecycle                   | → [docs/agent/plan-lifecycle.md](docs/agent/plan-lifecycle.md)                         |
| Understand plan enrichment workflow              | → [docs/agent/plan-enrichment.md](docs/agent/plan-enrichment.md)                       |
| Style CLI output                                 | → [docs/agent/cli-output-styling.md](docs/agent/cli-output-styling.md)                 |
| Implement script mode for shell integration      | → [docs/agent/cli-script-mode.md](docs/agent/cli-script-mode.md)                       |
| Use subprocess wrappers                          | → [docs/agent/subprocess-wrappers.md](docs/agent/subprocess-wrappers.md)               |
| Create kit CLI commands                          | → [docs/agent/kit-cli-commands.md](docs/agent/kit-cli-commands.md)                     |
| Understand kit code architecture                 | → [docs/agent/kit-code-architecture.md](docs/agent/kit-code-architecture.md)           |
| Delegate to agents from commands                 | → [docs/agent/command-agent-delegation.md](docs/agent/command-agent-delegation.md)     |
| Work with session logs (~/.claude/projects/)     | → [docs/agent/claude-code-session-layout.md](docs/agent/claude-code-session-layout.md) |
| Parse or analyze session logs                    | → [docs/agent/claude-code-session-layout.md](docs/agent/claude-code-session-layout.md) |
| Create hooks                                     | → [docs/agent/hooks.md](docs/agent/hooks.md)                                           |
| Write temp files for AI workflows                | → [docs/agent/scratch-storage.md](docs/agent/scratch-storage.md)                       |
| Understand project terms                         | → [docs/agent/glossary.md](docs/agent/glossary.md)                                     |
| Navigate documentation                           | → [docs/agent/guide.md](docs/agent/guide.md)                                           |
| View installed kits                              | → [@.agent/kits/kit-registry.md](.agent/kits/kit-registry.md)                          |

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

**Full guide**: [docs/agent/erk-architecture.md](docs/agent/erk-architecture.md)

## Project Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **CLI commands**: `kebab-case`
- **Claude artifacts**: `kebab-case` (commands, skills, agents, hooks in `.claude/`)
- **Brand names**: `GitHub` (not Github)

**Claude Artifacts:** All files in `.claude/` (commands, skills, agents, hooks) MUST use `kebab-case`. Use hyphens, NOT underscores. Example: `/my-command` not `/my_command`. Python scripts within artifacts may use `snake_case` (they're code, not artifacts).

**Worktree Terminology:** Use "root worktree" (not "main worktree") to refer to the primary git worktree created with `git init`. This ensures "main" unambiguously refers to the branch name, since trunk branches can be named either "main" or "master". In code, use the `is_root` field to identify the root worktree.

**CLI Command Organization:** Plan verbs are top-level (create, get, implement), worktree verbs are grouped under `erk wt`, stack verbs under `erk stack`. This follows the "plan is dominant noun" principle for ergonomic access to high-frequency operations. See [docs/agent/cli-command-organization.md](docs/agent/cli-command-organization.md) for complete decision framework.

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
