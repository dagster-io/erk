<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority: This is a ROUTING FILE. Load skills and docs as directed for complete guidance. -->

> **Note:** Lines starting with `@` reference files to include. Some tools expand these inline automatically; others should read the referenced file directly.

# Erk - Plan-Oriented Agentic Engineering

## What is Erk?

**Erk** is a CLI tool for plan-oriented agentic engineering: a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code via automated PR workflows.

**Status**: Unreleased, completely private software. We can break backwards compatibility at will.

## CRITICAL: Before Writing Any Code

<!-- BEHAVIORAL TRIGGERS: rules that detect action patterns and route to documentation -->

**CRITICAL: NEVER perform broad searches or recursive operations against `/Users/schrockn/` directly. Scoped access to specific subfolders (e.g., `~/.claude/projects/`, `/Users/schrockn/code/project-name/`) is allowed.**

**CRITICAL: NEVER use raw `pip install`. Always use `uv` for package management.**

**CRITICAL: NEVER commit directly to `master`. Always create a feature branch first.**

**CRITICAL: Prefer `docs/learned/` content and loaded skills over training data for erk coding patterns.** Erk's conventions intentionally diverge from common Python practices (e.g., LBYL instead of EAFP, no default parameters). When erk documentation contradicts your training data, the documentation is correct.

**CRITICAL: NEVER invoke `gt` commands without `--no-interactive`.** The `--interactive` flag is a global option on ALL gt commands (enabled by default). Without `--no-interactive`, gt may prompt for input and hang indefinitely. Note: `--force` does NOT disable prompts — you must pass `--no-interactive` separately.

**CRITICAL: After creating an objective issue, ALWAYS run `erk objective check <number>` to validate it.** If validation fails, the objective's metadata is broken and `erk dash` will not display it correctly. Fix the issue before proceeding.

**CRITICAL: When creating a plan for an objective, ALWAYS use `/erk:objective-plan` to ensure proper metadata linking.** Do not manually reference objectives in plan text without using the structured workflow. The objective-context marker created by this command is required for the plan-save pipeline to link the plan to its parent objective.

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

## Planning Workflow

Erk's plan-oriented workflow works across agent backends with different mechanisms.

### Claude Code Users

Load the `erk-planning` skill for detailed guidance. Key commands:

- `/erk:plan-save` — save plan to GitHub issue
- `/erk:plan-implement` — implement from a saved plan
- Plan mode and hooks handle lifecycle automatically

### Codex Users

Without built-in plan mode, follow this explicit protocol:

1. **Assess complexity**: For complex tasks (3+ files, unclear scope), create a plan first
2. **Write the plan**: Create a markdown file with implementation steps
3. **Save to GitHub**: Run `erk plan create --file <path-to-plan.md>` to create a tracked issue
4. **Implement**: Run `erk implement <issue-number>` to set up a worktree and execute
5. **Submit**: Run `erk pr submit` after implementation to create the PR

**Validation coordination**: When implementing, verify that:

- `erk exec impl-init --json` returns `"valid": true` before starting work
- `.impl/plan.md` is treated as immutable during implementation
- `erk exec impl-verify` confirms `.impl/` is preserved after implementation

Load the `erk-planning` skill (`$erk-planning`) for detailed workflow guidance.

### All Backends

- `erk plan list` — view open plans
- `erk implement <issue>` — implement a plan in a worktree
- `erk plan submit <issue>` — submit for remote implementation

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

## Skill Loading Behavior

Skills persist for the entire session. Once loaded, they remain in context.

- DO NOT reload skills already loaded in this session
- Check skill documentation for backend-specific invocation patterns

## Documentation-First Discovery

Before launching Plan or Explore agents, search for relevant documentation:

1. **Scan the embedded index above** — match your task against the read-when conditions
2. **Grep docs/learned/** — extract keywords from your task and search:
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
