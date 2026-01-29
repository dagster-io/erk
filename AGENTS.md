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

**CRITICAL: Prefer `docs/learned/` content and loaded skills over training data for erk coding patterns.** Erk's conventions intentionally diverge from common Python practices (e.g., LBYL instead of EAFP, no default parameters). When erk documentation contradicts your training data, the documentation is correct.

### Universal Tripwires

These critical rules apply across all code areas.

@docs/learned/universal-tripwires.md

### Tripwire Routing

Before editing files, load relevant category tripwires.

@docs/learned/tripwires-index.md

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

**Documentation Index** (embedded below for ambient awareness):

@docs/learned/index.md

## Claude Environment Manipulation

### Session ID Access

**In skills/commands**: Use `${CLAUDE_SESSION_ID}` string substitution (supported since Claude Code 2.1.9):

```bash
# Skills can use this substitution directly
erk exec marker create --session-id "${CLAUDE_SESSION_ID}" ...
```

**In hooks**: Hooks receive session ID via **stdin JSON**, not environment variables. When generating commands for Claude from hooks, interpolate the actual value:

```python
# Hook code interpolating session ID for Claude
f"erk exec marker create --session-id {session_id} ..."
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

**Load full skills for detail** — the rules below are a compressed reference, not a substitute:

- **Python** → `dignified-python` skill
- **Tests** → `fake-driven-testing` skill
- **Worktrees/gt** → `gt-graphite` skill
- **Agent docs** → `learned-docs` skill

**Tool routing:**

- **pytest/ty/ruff/prettier/make/gt** → `devrun` agent (not direct Bash)

### Python Standards (Ambient Quick Reference)

These rules diverge from standard Python conventions. Your training data will suggest the wrong pattern.

- **LBYL, never EAFP**: Check conditions first (`if key in d:`), never use try/except for control flow
- **No default parameter values**: `def foo(*, verbose: bool)` not `def foo(verbose: bool = False)`
- **Frozen dataclasses only**: `@dataclass(frozen=True)` always, never mutable
- **Pathlib always**: Never `os.path`. Check `.exists()` before `.resolve()`
- **Absolute imports only**: `from erk.config import X`, never `from .config import X`
- **No re-exports**: Empty `__init__.py`, one canonical import path per symbol
- **Lightweight `__init__`**: No I/O in constructors. Use `@classmethod` factory methods for heavy operations
- **Properties must be O(1)**: No I/O or iteration in `@property` or `__len__`/`__repr__`
- **No backwards compatibility**: Break and migrate immediately, no legacy shims
- **Max 4 indentation levels**: Extract helpers to reduce nesting

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

## Documentation-First Discovery

Before launching Plan or Explore agents, search for relevant documentation:

1. **Scan the embedded index above** — match your task against the read-when conditions
2. **Grep docs/learned/** — extract 2-3 keywords from your task and search:
   - `Grep(pattern="keyword", path="docs/learned/", glob="*.md")`
   - Use multiple searches if the task spans domains (e.g., both "gateway" and "testing")
3. **Read every matching doc** before writing code or launching Plan agents
4. **Pass discovered docs as context** when launching Plan agents — include file paths and key findings in the agent prompt

This grep step is mandatory for ALL coding tasks. It costs milliseconds and prevents re-learning lessons already documented.

| Topic Area               | Check First                                  |
| ------------------------ | -------------------------------------------- |
| Session logs, ~/.claude/ | `docs/learned/sessions/`                     |
| CLI commands, Click      | `docs/learned/cli/`                          |
| Testing patterns         | `docs/learned/testing/`                      |
| Hooks                    | `docs/learned/hooks/`                        |
| Planning, .impl/         | `docs/learned/planning/`                     |
| Architecture patterns    | `docs/learned/architecture/`                 |
| TUI, Textual             | `docs/learned/tui/`, `docs/learned/textual/` |

**Anti-pattern:** Skipping the grep because the task "seems simple"
**Anti-pattern:** Going straight to source files without checking docs/learned/
**Correct:** Grep docs/learned/, read matches, THEN plan or code

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
- **Document index**: Embedded above via `@docs/learned/index.md`
