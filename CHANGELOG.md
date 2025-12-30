# Changelog

All notable changes to erk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

As of bc6a308b0

### Major Changes

- The kit system has been completed eliminated. Erk installs its own artifacts directly with no user management required.
- We have moved back everything to be at repo-level. You must run claude at git repo root. This has simplified the architecture
- Migrate to static `erk exec` architecture, eliminating dynamic kit script loading (d82789f66)
- Merge git kit into erk artifacts with unified `/erk:git-pr-push` command namespace (e224d4279)
- Merge gt kit into erk artifacts, consolidating Graphite stack management (38de6381e)

### Added

- Add "Edit the plan" option to exit plan mode hook (d0ddc2889)
- Add `-f`/`--force` flag to `erk pr submit` for diverged branches (a8b46b01f)
- Add `show_hidden_commands` config option to control visibility of deprecated commands (91032b07d)

### Changed

- Move `/gt:pr-submit` to `/erk:pr-submit`, from the gt kit to the erk kit
- Move erk scripts to top-level `erk exec` from `erk kit exec erk` (7b3c2b2fd)
- Remove kit registry subsystem (e77266b27)
- Remove `kit list`, `remove`, `search`, and `show` commands - consolidated into `dot-agent` (0ab9f47c6)
- Rename `auto_restack_skip_dangerous` config to `auto_restack_require_dangerous_flag` with flipped default (9785d6fd5)
- Convert devrun from kit to single agent file (8ad2729fc)
- Remove dignified-python kit - consolidated into vanilla skill (d3f19bc5d)
- Consolidate dignified-python skill into single version-aware implementation (a058a259f)

### Fixed

- Fix `erk stack list` to show branches without worktrees using ancestor worktree (bc6a308b0)
- Fix: Validate GitHub PR base branch matches local trunk before landing (3897eb658)
- Fix AskUserQuestion option formatting in exit plan mode hook (ff62f6ac0)
- Fix hook subdirectory bug by using shared scratch directory utilities (7da1528fc)

### Removed

- Remove objectives feature (cf812796e)
- Disable session context embedding in plan save-to-issue command (8a85b62e6)

## [0.2.8] - 2025-12-18 06:51 PT

### Fixed

- Fix Bun crash when launching Claude Code CLI from tmux by conditionally redirecting TTY only when needed

## [0.2.7] - 2025-12-15 06:59 PT

### Major Changes

- Reorganize CLI commands for consistency with unified `list` and `checkout` patterns across worktrees, branches, and PRs
  - Move `submit` to `erk plan submit`
  - Add `erk branch` command group with `checkout` (`co`) and `list` (`ls`) subcommands
  - Rename `erk wt goto` to `erk wt checkout` with `co` alias
  - Remove top-level `list` and `delete` commands, now `erk wt list` and `erk wt delete`
- Remove standalone `erk kit sync` command, consolidated into `erk kit install --force`

### Added

- Add `.impl/` preservation guardrail to plan-implement workflow to prevent agents from deleting implementation plans - note: this may cause hard failures, please report if encountered
- Add `--all` flag to `erk wt delete` to close associated PR and plan
- Add copy logs button (`y` key) to plan detail screen
- Add config option `auto_restack_skip_dangerous` to skip `--dangerous` flag requirement
- Add `impl` alias for `erk implement` command
- Add prefix matching (PXXXX) for worktree-to-issue association
- Add PR URL display in quick-submit output

### Changed

- Clean up CLI help string organization and improve command grouping
- Improve devrun hook message to increase agent adherence to devrun pattern
- Move CHANGELOG.md to repository root for PyPI distribution
- Migrate PR and issue queries from GraphQL to REST API for rate limit avoidance
- Rename `/erk:submit-plan` command to `/erk:plan-submit` for consistency

### Fixed

- Fix release notes banner showing repeatedly when switching between worktrees with different erk versions
- Fix branch divergence error handling in PR submission with actionable remediation message
- Fix PR submissions to use Graphite parent branch instead of trunk

### Removed

- Remove SESSION_CONTEXT environment variable for session ID passing

## [0.2.5] - 2025-12-12 14:30 PT

### Major Changes

- Publish `erk` and `erk-shared` packages to PyPI - install via `uv pip install erk` or run directly with `uvx erk`
- Relocate all erk-managed documentation from `docs/agent/` and `.claude/docs/` to unified `.erk/docs/` structure
- Add hook execution logging system with new "Hooks" section in `erk doctor` for health monitoring
- Add integrated release notes system with version change detection and `erk info release-notes` command

### Added

- Add link indicator to PR display in plan dashboard for quick GitHub access
- Add `--force` flag to bypass open PR checks with confirmation in navigation commands
- Add `--dangerous` flag to `erk pr auto-restack` and `erk pr sync` commands for explicit opt-in to risky operations

### Changed

- Remove legacy `dot-agent.toml` configuration and migrate to `kits.toml`
- Add `erk doctor` checks for legacy documentation locations

### Fixed

- Fix release notes banner incorrectly shown on version downgrade in multi-worktree setups
- Fix nested bullet indentation in release notes parsing and display

### Removed

- Remove outdated erk skill documentation from `.claude/skills/erk/`

## [0.2.3] - 2025-12-12

### Added

- Add orphaned artifact detection for `.claude/` directory
- Add hooks disabled check to `erk doctor` command with warning indicator
- Add critical safety guardrail against automatic remote pushes

### Changed

- Eliminated the `dot-agent-kit` package entirely and consolidated config:
  - Repository config moved to `.erk/config.toml` with legacy fallback support
  - Consolidate into `erk-kits` + `erk.kits`
  - Remove `dot-agent.toml` requirement, use `kits.toml` for project detection
  - Fix `dev_mode` config to use `[tool.erk]` instead of deprecated `[tool.dot-agent]`
- Consolidate PR submission into unified two-layer architecture (core + Graphite)

### Fixed

- Fix detect no-work-events failure mode in auto-restack command
- Fix OSError "argument list too long" by passing prompt via stdin instead of command line
- Fix PR summary generation by passing `PR_NUMBER` through workflow environment
- Fix `erk pr check` step numbering in plan-implement command
- Fix `gt quick-submit` hanging by adding `--no-edit` and `--no-interactive` flags
- Fix GitHub GraphQL array and object variable passing in gh CLI commands

## [0.2.2] - 2025-12-11

### Added

- Release notes system with version change detection and `erk info release-notes` command
- Sort plans by recent branch activity with `--sort` flag in `erk plan list`

### Changed

- Improved `erk doctor` with GitHub workflow permission checks
- Eliminated dot-agent CLI, consolidated all commands into erk
