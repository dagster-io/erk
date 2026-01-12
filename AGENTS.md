<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority: This is a ROUTING FILE. Load skills and docs as directed for complete guidance. -->

# Erk - Plan-Oriented Agentic Engineering

## What is Erk?

**Erk** is a CLI tool for plan-oriented agentic engineering: a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code via automated PR workflows.

**Status**: Unreleased, completely private software. We can break backwards compatibility at will.

## CRITICAL: Before Writing Any Code

<!-- BEHAVIORAL TRIGGERS: rules that detect action patterns and route to documentation -->

**CRITICAL: NEVER search, read, or access `/Users/schrockn/` directory**

**CRITICAL: NEVER use raw `pip install`. Always use `uv` for package management.**

**CRITICAL: NEVER commit directly to `master`. Always create a feature branch first.**

@docs/learned/tripwires.md

**Load these skills FIRST:**

- **Python code** → `dignified-python` skill (LBYL, modern types, ABC interfaces)
- **Test code** → `fake-driven-testing` skill (5-layer architecture, test placement)
- **Dev tools** → Use `devrun` agent (NOT direct Bash for pytest/ty/ruff/prettier/make/gt)

## Core Architecture

**Tech Stack:** Python 3.10+ (uv), Git worktrees, Graphite (gt), GitHub CLI (gh), Claude Code

**Project Structure:**

```
erk/
├── .claude/          # Claude Code commands, skills, hooks
├── .erk/             # Erk configuration, scratch storage
├── docs/learned/     # Agent-generated documentation
├── src/erk/          # Core implementation
└── tests/            # Test suite (5-layer fake-driven architecture)
```

**Design Principles:** Plan-first workflow, worktree isolation, agent-driven development, documentation as code.

## How Agents Work

This file routes to skills and docs; it doesn't contain everything.

**Key Skills** (loaded on-demand):

- `dignified-python`: Python coding standards (LBYL, frozen dataclasses, modern types)
- `fake-driven-testing`: 5-layer test architecture with comprehensive fakes
- `gt-graphite`: Worktree stack mental model
- `devrun`: READ-ONLY agent for running pytest/ty/ruff/make

**Documentation Index**: [docs/learned/index.md](docs/learned/index.md) - complete registry with "read when..." conditions.

## Claude Environment Manipulation

### Session ID Injection

Hooks receive session ID via **stdin JSON**, NOT environment variables. When generating commands for Claude, interpolate the actual value:

```python
# CORRECT - Claude receives the actual value
f"erk exec marker create --session-id {session_id} ..."

# WRONG - Claude can't expand this variable
"erk exec marker create --session-id $CLAUDE_CODE_SESSION_ID ..."
```

### Hook → Claude Communication

- Hook stdout becomes system reminders in Claude's context
- Exit codes block or allow tool calls

### Modified Plan Mode Behavior

Erk modifies plan mode to add a save-or-implement decision:

1. Claude is prompted: "Save the plan to GitHub, or implement now?"
2. **Save**: Claude runs `/erk:plan-save` to create a GitHub issue
3. **Implement now**: Claude proceeds to implementation

---

# Erk Coding Standards

## Before You Code

**Mandatory skills:**

- **Python** → `dignified-python` skill
- **Tests** → `fake-driven-testing` skill

**Context-specific:**

- **Worktrees/gt** → `gt-graphite` skill
- **Agent docs** → `learned-docs` skill

**Tool routing:**

- **pytest/ty/ruff/prettier/make/gt** → `devrun` agent (not direct Bash)

### devrun Agent Restrictions

**FORBIDDEN prompts:**

- "fix any errors that arise"
- "make the tests pass"
- Any prompt implying devrun should modify files

**REQUIRED pattern:**

- "Run [command] and report results"
- "Execute [command] and parse output"

devrun is READ-ONLY. It runs commands and reports. Parent agent handles all fixes.

## Skill Loading Behavior

Skills persist for the entire session. Once loaded, they remain in context.

- DO NOT reload skills already loaded in this session
- Hook reminders fire as safety nets, not commands
- Check if loaded: Look for `<command-message>The "{name}" skill is loading</command-message>` earlier in conversation

## Documentation-First Exploration

Before exploring any topic:

1. **First** check `docs/learned/index.md` for existing documentation
2. **Read** relevant docs to understand what's already documented
3. **Only then** explore raw files or spawn Explore for gaps/validation

| Topic Area               | Check First                                  |
| ------------------------ | -------------------------------------------- |
| Session logs, ~/.claude/ | `docs/learned/sessions/`                     |
| CLI commands, Click      | `docs/learned/cli/`                          |
| Testing patterns         | `docs/learned/testing/`                      |
| Hooks                    | `docs/learned/hooks/`                        |
| Planning, .impl/         | `docs/learned/planning/`                     |
| Architecture patterns    | `docs/learned/architecture/`                 |
| TUI, Textual             | `docs/learned/tui/`, `docs/learned/textual/` |

**Anti-pattern:** Going straight to `~/.claude/projects/` to explore session files
**Correct:** First reading `docs/learned/sessions/layout.md` and `jsonl-schema-reference.md`

### Including Documentation in Plans

When creating implementation plans, include a "Related Documentation" section listing skills to load and docs relevant to the implementation approach.

## Worktree Stack Quick Reference

- **UPSTACK** = away from trunk (toward leaves/top)
- **DOWNSTACK** = toward trunk (main at BOTTOM)
- **Full details**: Load `gt-graphite` skill for complete visualization and mental model

## Project Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **CLI commands**: `kebab-case`
- **Claude artifacts**: `kebab-case` (commands, skills, agents, hooks in `.claude/`)
- **Brand names**: `GitHub` (not Github)

**Claude Artifacts:** All files in `.claude/` MUST use `kebab-case`. Use hyphens, NOT underscores. Example: `/my-command` not `/my_command`.

**Worktree Terminology:** Use "root worktree" (not "main worktree") to refer to the primary git worktree. In code, use the `is_root` field.

**CLI Command Organization:** Plan verbs are top-level (create, get, implement), worktree verbs under `erk wt`, stack verbs under `erk stack`. See [CLI Development](docs/learned/cli/) for complete decision framework.

## Project Constraints

**No time estimates in plans:**

- FORBIDDEN: Time estimates (hours, days, weeks)
- FORBIDDEN: Velocity predictions or completion dates
- FORBIDDEN: Effort quantification

**Test discipline:**

- FORBIDDEN: Writing tests for speculative or "maybe later" features
- ALLOWED: TDD workflow (write test → implement feature → refactor)
- MUST: Only test actively implemented code

**CHANGELOG discipline:**

- FORBIDDEN: Modifying CHANGELOG.md directly
- ALLOWED: Use `/local:changelog-update` to sync after merges to master

## Documentation Hub

- **Full navigation guide**: [docs/learned/guide.md](docs/learned/guide.md)
- **Document index with "read when..." conditions**: [docs/learned/index.md](docs/learned/index.md)
