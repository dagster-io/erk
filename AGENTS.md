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

| If you're about to...                            | STOP! Check this instead                                                             |
| ------------------------------------------------ | ------------------------------------------------------------------------------------ |
| Write Python code                                | → Load `dignified-python-313` skill FIRST                                            |
| Write or modify tests                            | → Load `fake-driven-testing` skill FIRST                                             |
| Run pytest, pyright, ruff, prettier, make, or gt | → Use `devrun` agent (Task tool), NOT Bash                                           |
| Import time or use time.sleep()                  | → Use `context.time.sleep()` instead (see erk-architecture.md#time-abstraction)      |
| Work with Graphite stacks                        | → Load `gt-graphite` skill for stack visualization and terminology                   |
| Find documentation on a topic                    | → [docs/agent/index.md](docs/agent/index.md) (auto-generated index with `read_when`) |
| Understand project terms                         | → [docs/agent/glossary.md](docs/agent/glossary.md)                                   |
| View installed kits                              | → [@.agent/kits/kit-registry.md](.agent/kits/kit-registry.md)                        |

## Graphite Stack Quick Reference

- **UPSTACK** = away from trunk (toward leaves/top)
- **DOWNSTACK** = toward trunk (main at BOTTOM)
- **Full details**: Load `gt-graphite` skill for complete visualization and mental model

## Erk-Specific Architecture

**Full guide**: [docs/agent/erk-architecture.md](docs/agent/erk-architecture.md)

## Project Naming Conventions

| Element             | Convention   |
| ------------------- | ------------ |
| Functions/variables | `snake_case` |
| Classes             | `PascalCase` |
| CLI commands        | `kebab-case` |
| Claude artifacts    | `kebab-case` |

**Full guide**: [docs/agent/conventions.md](docs/agent/conventions.md)

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

- **All docs (with `read_when`)**: [docs/agent/index.md](docs/agent/index.md)
- **Installed kits**: [@.agent/kits/kit-registry.md](.agent/kits/kit-registry.md)
- **Python standards**: Load `dignified-python-313` skill
- **Test architecture**: Load `fake-driven-testing` skill
- **Graphite stacks**: Load `gt-graphite` skill
