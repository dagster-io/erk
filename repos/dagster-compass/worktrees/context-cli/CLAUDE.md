# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Use devrun Agent for CLI Tools

**Use the Task tool with devrun agent for development tools instead of Bash.**

| If you're about to run...    | STOP! Use this instead                                               |
| ---------------------------- | -------------------------------------------------------------------- |
| `make ...`                   | → Task(subagent_type="devrun", prompt="Execute: make ...")           |
| `uv run pytest ...`          | → Task(subagent_type="devrun", prompt="Execute: uv run pytest ...")  |
| `uv run pyright ...`         | → Task(subagent_type="devrun", prompt="Execute: uv run pyright ...") |
| `uv run ruff ...`            | → Task(subagent_type="devrun", prompt="Execute: uv run ruff ...")    |
| `gt ...` (Graphite commands) | → Task(subagent_type="devrun", prompt="Execute: gt ...")             |

**Why use devrun agent:**

- Token efficiency: Subagent contexts don't pollute parent context
- Cost optimization: Uses Haiku model for command execution (cheaper than Sonnet)
- Output parsing: Automatically parses tool output into structured format
- Context isolation: Large command outputs stay in subagent

**Example:**

```python
# ❌ WRONG: Direct Bash for CLI tools
Bash("uv run pytest tests/")
Bash("uv run pyright packages/")

# ✅ CORRECT: Use devrun agent
Task(subagent_type="devrun", description="Run tests", prompt="Execute: uv run pytest tests/")
Task(subagent_type="devrun", description="Type check", prompt="Execute: uv run pyright packages/")
```

**What CAN use Bash directly:**

- Git operations: `git status`, `git log`, `git diff`, `git branch`
- File system: `ls`, `cat`, `find`, `grep`
- Simple commands: `echo`, `pwd`, `tree`

## Project Overview

This is the "Compass" project - a Compass Bot (csbot) system that provides intelligent data analysis capabilities through Slack bots and contextual data management. The system includes:

- **csbot Client**: Core client library for profile and connection management
- **Context Store**: Document-based context storage with search capabilities and GitHub integration
- **Slack Bot**: AI-powered data analysis bot with streaming responses and analytics
- **CS Admin**: CLI tool for managing contextstore projects, datasets, and connections

## Development Commands

### Installation and Setup

```bash
# Install dependencies using uv
uv sync

# Install with development dependencies
uv sync --group dev
```

**IMPORTANT:** After initial `uv sync --group dev`, the package is installed in **editable mode**. This means:

- ✅ Code changes in Python modules are immediately reflected - no re-sync needed
- ✅ CLI commands (`compass-dev`, `ctx-admin`, `slackbot`) pick up changes automatically
- ❌ Only re-run `uv sync --group dev` if you modify `pyproject.toml` (add dependencies, change entry points, etc.)

## Development Workflow

### Code Quality Checks

- CRITICAL: Run make pyright and make ruff after every .py change.
- CRITICAL: Run make prettier after every .md, .yml, or .yaml change.

### Testing

The project separates unit tests from integration tests using directory structure:

- **Unit tests** (`tests/`): Fast tests with mocked dependencies, no external I/O
- **Integration tests** (`tests/integration/`): Tests with real external systems (PostgreSQL, Redis, git operations, etc.)

Run tests using make commands:

```bash
make test              # Unit tests only (fast)
make test-integration  # Integration tests only
make test-all         # All tests
```

See `packages/csbot/tests/README.md` for detailed classification criteria and organization guidelines.

## Python Coding Standards

**All Python code in this repository must follow the dignified-python coding standards.**

See `.claude/skills/dignified-python/SKILL.md` for complete standards including:

- **LBYL exception handling** - Check conditions before acting, never use exceptions for control flow
- **Python 3.13+ type syntax** - Use `list[str]`, `dict[str, int]`, `str | None` (NO `List`, `Optional`, `Union`)
- **Absolute imports only** - Never use relative imports
- **pathlib for all file operations** - Check `.exists()` before `.resolve()`
- **ABC-based interfaces** - Use `abc.ABC`, not `Protocol`
- **Explicit error boundaries** - Handle exceptions only at CLI/API boundaries
- **Max 4 indent levels** - Extract helper functions if deeper
- **Immutable data structures** - Default to `@dataclass(frozen=True)`
- **No backwards compatibility** - Break APIs and migrate callsites unless explicitly required

The dignified-python skill is automatically loaded when editing Python files.

## Architectural Patterns

The project follows documented cross-cutting patterns for consistency and testability:

- **[Dependency Injection](docs/patterns/dependency-injection.md)** - Constructor injection with production defaults for testability without mocking
- **[Time Abstraction](docs/patterns/time-abstraction.md)** - Injecting time providers (`DatetimeNow`, `AsyncSleep`) for deterministic testing

See [docs/patterns/README.md](docs/patterns/README.md) for complete pattern catalog and usage guidelines.

**When writing time-dependent code:**

- Always inject `DatetimeNow`, `SecondsNow`, or `AsyncSleep` from `csbot.utils.time`
- Use production defaults: `system_datetime_now`, `system_async_sleep`
- In tests, use `FakeTimeProvider` for instant, deterministic time control
- Never use `asyncio.sleep()` in production code that will be tested

## Async/Sync Interface Pattern

When you need to maintain parallel sync and async interfaces for the same business logic, consult `@src/csbot/utils/async_thread.py` for a Protocol-based pattern that:

- Eliminates code duplication between sync and async implementations
- Provides automatic conversion through decorators
- Maintains type safety through protocols
- Creates a single source of truth for business logic
- Allows easy testing of sync logic without async complexity

This pattern is particularly useful when you have business logic that needs to be available in both synchronous and asynchronous contexts without duplicating the implementation.

## Running Applications

The project provides several CLI tools:

- **`slackbot`**: Slack bot for AI-powered data analysis
- **`ctx-admin`**: Context Store administration tool
- **`compass-dev`**: Developer utilities

Use `--help` with any command to see current options and usage.

For testing, the project uses `pytest` via `uv run pytest`.

## Important Notes

- The system requires proper environment variables for GitHub tokens and secret stores
- Slack bot operations depend on Redis being available
- Context store operations work with local Git repositories and can sync with GitHub
- All SQL connections are abstracted through the csbot client profile system

## Slack Bot Development

### Welcome Message Testing

- **Implementation**: Welcome message triggered by `!welcome` command in `src/csbot/slackbot/channel_bot/bot.py`
- **Message Generation**: Logic in `src/csbot/slackbot/admin_commands.py` (`_build_governance_welcome_message` method)
- **Tests**: Located in `packages/csbot/tests/test_member_join_behavior.py` under `TestGovernanceWelcomeMessage` class
- **Manual Testing**: Run `slackbot start` and type `!welcome` in a Slack governance channel
