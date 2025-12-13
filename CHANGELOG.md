# Changelog

All notable changes to erk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

As of b201e6e8b

### Major Changes

- Reorganize CLI commands: move `submit` to `erk plan submit`, elevate `list` and `delete` to top-level (49c41562d)

### Added

- Add `.impl/` preservation guardrail to plan-implement workflow to prevent agents from deleting implementation plans - note: this may cause hard failures, please report if encountered (635642e33)

### Changed

- Clean up CLI help string organization and improve command grouping (00f03268f)
- Improve devrun hook message to increase agent adherence to devrun pattern (b5e949b45)
- Move CHANGELOG.md to repository root for PyPI distribution (1fe3629bf)

### Fixed

- Fix release notes banner showing repeatedly when switching between worktrees with different erk versions (3c6ef9c62)
- Fix branch divergence error handling in PR submission with actionable remediation message (2907ca360)

### Removed

- Remove SESSION_CONTEXT environment variable for session ID passing (5f6dd1214)

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
