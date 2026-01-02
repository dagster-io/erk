# Changelog

All notable changes to erk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.3.2] - 2026-01-02 12:30 PT

### Major Changes

- **dignified-review**: Added AI-assisted code review as an optionally installed GitHub Action. Ensures compliance with dignified-python standards during code review by leaving comments on PRs. Comments are designed to be resolved via `/erk:pr-address`.

- **Top-level `erk land` command**: Promoted land from `erk pr land` to `erk land`. Now accepts PR numbers, URLs, or branch names. Includes shell aliases `br land` and `branch land`. Landing PRs is a high-frequency operation that deserves top-level access.

- **Cross-repo plan storage**: Plans can now be stored in a separate repository. Configure via `.erk/config.toml` with `[plans] repo = "owner/repo"`. This avoids polluting the main codebase with plan issues, particularly valuable for open source repos like dagster where we don't want erk-specific artifacts.

- **erk-statusline**: Added the erk statusline. Optionally installable via `erk init --statusline`. Displays current branch, worktree, GitHub checks status, PR info, and more. Provides at-a-glance visibility into your development state without running commands.

- **Graphite opt-in**: Graphite is now optional. Not everyone uses Graphite, so although you don't get stacking features, Graphite-less operation is now a fully supported workflow. Commands gracefully degrade to standard git operations.

### Added

- Add command logging for CLI audit trail
- Add step-based progress tracking with GitHub metadata sync
- Add per-artifact version and hash tracking for health monitoring
- Add dynamic tripwire enforcement system
- Add erk-statusline configuration to init and health checks
- Add copy-pasteable commands section to plan issues
- Add auto-rebase when local branch is behind remote before push
- Add `--session-id` flag to marker CLI commands for explicit session ID
- Add configurable `default` parameter to `user_confirm` function

### Changed

- Restructure init command with stepped flow and status line setup
- Standardize GitHub Actions workflow naming to kebab-case

### Fixed

- Fix `erk pr checkout` for stacked PRs
- Fix dignified-python skill LBYL vs try/except guidance
- Fix `erk wt delete --all` to show accurate PR/plan status in planning phase
- Fix confirmation prompt output to stderr for consistency
- Fix pr-address skill handling of outdated review threads
- Fix changelog commit hash marker parsing to expect backtick formatting
- Fix frontmatter deprecation warning cluttering test output
- Fix GitHub Actions shell specification in review workflows
- Fix Claude Code installation path in Docker image
- Fix status comparison: compare against `StatusData.loading()` not `is None`

## [0.3.1] - 2025-12-31 15:52 PT

### Fixed

- Make step extraction gracefully degrade to empty list on empty LLM output

### Changed

- Update release process documentation and consolidate into RELEASING.md

## [0.3.0] - 2025-12-31 14:13 PT

### Release Overview

This release dramatically simplifies erk's architecture by eliminating the kit system and consolidating artifact management into a single, automated workflow.

#### Kit System Eliminated

The kit system has been completely removed. Previously, users installed and managed "kits" (bundles of skills, commands, and agents) per-project. Now erk owns its artifacts directly:

- No `erk kit install`, `erk kit sync`, or kit registry commands
- Artifacts are bundled with erk itself and synced automatically
- One less concept to understand, one less thing to manage

#### Unified Artifact Management

erk now maintains a set of **bundled artifacts** that it syncs to target projects:

- **Skills**: `dignified-python`, `learned-docs`, `erk-diff-analysis`
- **Commands**: All `/erk:*` namespace commands (`/erk:plan-implement`, `/erk:pr-submit`, etc.)
- **Agents**: `devrun` (for running pytest/ty/ruff/make)
- **Workflows**: `erk-impl.yml` (for remote plan implementation via GitHub Actions)
- **Hooks**: `user-prompt-hook` and `exit-plan-mode-hook` (session management and plan tracking)

Running `erk init` or `erk artifact sync`:

1. Copies file-based artifacts to `.claude/` and `.github/workflows/`
2. Adds hook configurations to `.claude/settings.json`
3. Stamps the version in `.erk/state.toml` for staleness detection

`erk doctor` and `erk artifact check` detect stale, missing, or orphaned artifacts—including missing hook configurations. Projects keep full ownership of `.claude/`; erk only manages its namespaced artifacts.

#### Repo-Level Constraint

erk now requires Claude to be launched from the git repository root. This simplifies worktree detection, artifact paths, and context creation. If you previously ran Claude from subdirectories, launch from the repo root instead. This matches how most users already work and provides a stable foundation.

#### Global Install Required (UVX Not Supported)

We explored using `uvx erk` for zero-install usage, but this isn't feasible due to shell integration. Commands like `erk implement`, `erk up`, `erk down`, and `erk wt checkout` change your shell's working directory—something only a shell function can do. This requires a shell wrapper function (installed via `erk init --shell`) that calls a persistent `erk` binary in your PATH.

**The solution is simple**: Install erk globally with `uv tool install erk`. erk handles the rest:

- Each repo has a `.erk/required-erk-uv-tool-version` file specifying the required version
- If your installed version doesn't match, erk warns you immediately with the fix: `uv tool upgrade erk`
- One person on the team updates the version file; everyone else follows the prompt

You don't install erk into each project—just keep your global tool current and artifacts synced. erk tells you when action is needed.

---

### Major Changes

- Extend artifact management to GitHub workflows with model configurability and OAuth support
- The kit system has been completely eliminated. erk installs its own artifacts directly with no user management required.
- We have moved back everything to be at repo-level. You must run claude at git repo root. This has simplified the architecture
- Migrate to static `erk exec` architecture, eliminating dynamic kit script loading
- Merge git kit into erk artifacts with unified `/erk:git-pr-push` command namespace
- Merge gt kit into erk artifacts, consolidating Graphite stack management
- Delete kit infrastructure entirely, relocating utilities to erk core packages
- Add unified artifact distribution system with discovery, sync, and staleness detection
- Relocate all erk documentation from `.erk/docs/agent` to `docs/learned/`

### Added

- Add uvx/`uv tool run` detection with warning and confirmation prompt for shell integration commands
- Add missing artifact detection to complement orphan detection for bidirectional artifact health checks
- Add doctor checks for exit-plan-hook and required-version validation
- Add erk-managed indicator badges to artifact list command output
- Add retry logic with exponential backoff to prompt executor for transient API failures
- Add `impl` command alias for `implement` in shell integration
- Establish `.erk/prompt-hooks/` directory for AI-readable hook instructions
- Add "Edit the plan" option to exit plan mode hook
- Add `-f`/`--force` flag to `erk pr submit` for diverged branches
- Add `show_hidden_commands` config option to control visibility of deprecated commands
- Add hook initialization support to `erk init` command with `--hooks` flag
- Add backup file creation when modifying settings.json
- Add legacy pattern detection health checks for early dogfooders
- Add tool version checking to warn when installed erk is outdated
- Add automatic `--pull/--no-pull` option to `erk pr land` command
- Always show last commit time in branch list by default
- Add `reply-to-discussion-comment` exec command for formatted PR comment replies
- Implement LLM-based step extraction for plan implementation folders

### Changed

- Restrict artifact sync to only copy bundled items, preventing dev-only artifacts from leaking into projects
- Make missing artifacts detection fail instead of warn
- Rename `/erk:save-plan` command to `/erk:plan-save` for consistency
- Integrate artifact syncing into `erk init` command
- Rename agent-docs skill to learned-docs
- Flatten agent folders to top-level artifacts
- Move `/gt:pr-submit` to `/erk:pr-submit`, from the gt kit to the erk kit
- Move erk scripts to top-level `erk exec` from `erk kit exec erk`
- Remove kit registry subsystem
- Remove `kit list`, `remove`, `search`, and `show` commands - consolidated into `dot-agent`
- Rename `auto_restack_skip_dangerous` config to `auto_restack_require_dangerous_flag` with flipped default
- Convert devrun from kit to single agent file
- Remove dignified-python kit - consolidated into vanilla skill
- Consolidate dignified-python skill into single version-aware implementation
- Rename `gt-graphite` skill to `gt` with simplified directory structure
- Streamline devrun agent to use Sonnet model with minimal documentation
- Standardize erk hook ID to `user-prompt-hook` via `erk exec` command
- Rename health check names to kebab-case format
- Scrub all kit references from repository
- Remove support for standalone docs in `.claude/docs/` directory; use skills instead
- Make PR parsing stricter by requiring github.com URLs
- Eliminate kit.yaml manifest files, use frontmatter-based artifact discovery
- Remove `erk kit` CLI commands and simplify artifact management

### Fixed

- Fix missing error handling for deleted plan comment references with graceful fallback
- Fix artifact check to display only installed artifacts instead of bundled defaults
- Fix artifact sync path detection for editable installs
- Fix function name import and call in post_plan_comment script
- Fix `erk stack list` to show branches without worktrees using ancestor worktree
- Fix: Validate GitHub PR base branch matches local trunk before landing
- Fix AskUserQuestion option formatting in exit plan mode hook
- Fix hook subdirectory bug by using shared scratch directory utilities
- Fix shell completion context creation in resilient parsing mode
- Re-implement branch divergence check for PR submission with pre-flight validation
- Fix LLM step extraction robustness by upgrading to Sonnet model
- Fix LLM empty output handling in step extraction with diagnostic logging
- Add issue title to plan save output

### Removed

- Remove objectives feature
- Disable session context embedding in plan save-to-issue command

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
