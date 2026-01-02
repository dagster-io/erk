<!-- AGENT NOTICE: This file is loaded automatically. Read FULLY before writing code. -->
<!-- Priority: This is a ROUTING FILE. Load skills and docs as directed for complete guidance. -->

# Erk - Plan-Oriented Agentic Engineering

## What is Erk?

**Erk** is a CLI tool for plan-oriented agentic engineering: a workflow where AI agents create implementation plans, execute them in isolated worktrees, and ship code via automated PR workflows.

**Status**: Unreleased, completely private software. We can break backwards compatibility at will based on developer preferences.

## Core Architecture

**Tech Stack:**

- Python 3.10+ (managed with `uv`)
- Git worktrees for parallel development
- Graphite (`gt`) for stacked PRs
- GitHub CLI (`gh`) for PR management
- Claude Code for AI-driven development

**Project Structure:**

```
erk/
├── .claude/          # Claude Code commands, skills, hooks
├── .erk/             # Erk configuration, scratch storage
├── docs/learned/     # Agent-generated documentation
├── src/erk/          # Core implementation
└── tests/            # Test suite (5-layer fake-driven architecture)
```

**Design Principles:**

- **Plan-first workflow**: Create plans → implement → ship (often without IDE)
- **Worktree isolation**: Each feature branch gets its own worktree
- **Agent-driven**: Claude Code executes implementation plans autonomously
- **Documentation as code**: Agents extract reusable patterns into `docs/learned/`

## How Agents Work on This Project

**Routing Model**: This file (AGENTS.md) is a routing document. It doesn't contain all information—it directs you to load the right skills and documentation based on the task.

**Key Skills** (loaded on-demand):

- `dignified-python`: Python coding standards (LBYL, frozen dataclasses, modern types)
- `fake-driven-testing`: 5-layer test architecture with comprehensive fakes
- `gt-graphite`: Worktree stack mental model
- `devrun`: READ-ONLY agent for running pytest/ty/ruff/make

**Documentation Index**: See [docs/learned/index.md](docs/learned/index.md) for complete document registry with "read when..." conditions.

---

# Erk Coding Standards

## ⚠️ CRITICAL: Before Writing Any Code

<!-- These are BEHAVIORAL TRIGGERS: rules that detect action patterns and route to documentation -->

**CRITICAL: NEVER search, read, or access `/Users/schrockn/` directory**

**CRITICAL: NEVER use raw `pip install`. Always use `uv` for package management.**

**CRITICAL: NEVER commit directly to `master`. Always create a feature branch first.**

**CRITICAL: NEVER push code to remote (git push, gt ss, gt submit) unless the user explicitly requests it.**

@docs/learned/tripwires.md

**Load these skills FIRST:**

- **Python code** → `dignified-python` skill (LBYL, modern types, ABC interfaces)
- **Test code** → `fake-driven-testing` skill (5-layer architecture, test placement)
- **Dev tools** → Use `devrun` agent (NOT direct Bash for pytest/ty/ruff/prettier/make/gt)

## Skill Loading Behavior

**Skills persist for the entire session.** Once loaded, they remain in context.

- **DO NOT reload skills already loaded in this session**
- Hook reminders fire as safety nets, not commands
- If you see a reminder for an already-loaded skill, acknowledge and continue

**Check if loaded**: Look for `<command-message>The "{name}" skill is loading</command-message>` earlier in conversation

## Routing: What to Load Before Writing Code

### Tier 1: Mandatory Skills (ALWAYS Load First)

These fundamentally change how you write code. Load before ANY code work:

- **Writing Python** → Load `dignified-python` skill
- **Writing or modifying tests** → Load `fake-driven-testing` skill

### Tier 2: Context-Specific Skills

Load when the context applies:

- **Worktree stacks, `gt` commands** → Load `gt-graphite` skill
- **Writing agent documentation** → Load `learned-docs` skill

### Tier 3: Tool Routing

Use agents instead of direct Bash:

- **pytest, ty, ruff, prettier, make, gt** → Use `devrun` agent (Task tool)

#### devrun Agent - Prompt Restrictions

**FORBIDDEN prompts to devrun:**

- ❌ "fix any errors that arise"
- ❌ "make the tests pass"
- ❌ "update the imports"
- ❌ "correct the issues"
- ❌ Any prompt implying devrun should modify files

**REQUIRED prompt pattern:**

- ✅ "Run [command] and report results"
- ✅ "Execute [command] and parse output"

devrun is READ-ONLY. It runs commands and reports. Parent agent handles all fixes.

### Tier 4: Documentation Lookup

For detailed reference, consult the documentation index which maps each document to specific "read when..." conditions:

→ **[docs/learned/index.md](docs/learned/index.md)** - Complete document registry (auto-generated, always current)

#### Including Documentation in Plans

When creating implementation plans, include a "Related Documentation" section listing:

- Skills to load before implementing
- Docs relevant to the implementation approach

This ensures implementing agents have access to documentation you discovered during planning.

## Worktree Stack Quick Reference

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

**Full guide**: [Architecture](docs/learned/architecture/)

## Project Naming Conventions

- **Functions/variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **CLI commands**: `kebab-case`
- **Claude artifacts**: `kebab-case` (commands, skills, agents, hooks in `.claude/`)
- **Brand names**: `GitHub` (not Github)

**Claude Artifacts:** All files in `.claude/` (commands, skills, agents, hooks) MUST use `kebab-case`. Use hyphens, NOT underscores. Example: `/my-command` not `/my_command`. Python scripts within artifacts may use `snake_case` (they're code, not artifacts).

**Worktree Terminology:** Use "root worktree" (not "main worktree") to refer to the primary git worktree created with `git init`. This ensures "main" unambiguously refers to the branch name, since trunk branches can be named either "main" or "master". In code, use the `is_root` field to identify the root worktree.

**CLI Command Organization:** Plan verbs are top-level (create, get, implement), worktree verbs are grouped under `erk wt`, stack verbs under `erk stack`. This follows the "plan is dominant noun" principle for ergonomic access to high-frequency operations. See [CLI Development](docs/learned/cli/) for complete decision framework.

## Project Constraints

**No time estimates in plans:**

- 🔴 **FORBIDDEN**: Time estimates (hours, days, weeks)
- 🔴 **FORBIDDEN**: Velocity predictions or completion dates
- 🔴 **FORBIDDEN**: Effort quantification

**Test discipline:**

- 🔴 **FORBIDDEN**: Writing tests for speculative or "maybe later" features
- ✅ **ALLOWED**: TDD workflow (write test → implement feature → refactor)
- 🔴 **MUST**: Only test actively implemented code

**CHANGELOG discipline:**

- 🔴 **FORBIDDEN**: Modifying CHANGELOG.md directly
- ✅ **ALLOWED**: Use `/local:changelog-update` to sync after merges to master
- CHANGELOG updates happen post-merge, not during PR development

## Documentation Hub

- **Full navigation guide**: [docs/learned/guide.md](docs/learned/guide.md)
- **Document index with "read when..." conditions**: [docs/learned/index.md](docs/learned/index.md)
