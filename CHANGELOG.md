# Changelog

All notable changes to erk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

As of af8fa25c9

### Major Changes

- Extend artifact management to GitHub workflows with model configurability and OAuth support (de0bfa279, 52579c0e4, f7597c52e)
- The kit system has been completed eliminated. Erk installs its own artifacts directly with no user management required.
- We have moved back everything to be at repo-level. You must run claude at git repo root. This has simplified the architecture
- Migrate to static `erk exec` architecture, eliminating dynamic kit script loading (d82789f66)
- Merge git kit into erk artifacts with unified `/erk:git-pr-push` command namespace (e224d4279)
- Merge gt kit into erk artifacts, consolidating Graphite stack management (38de6381e)
- Delete kit infrastructure entirely, relocating utilities to erk core packages (745a278b5)
- Add unified artifact distribution system with discovery, sync, and staleness detection (e1d672e1b)
- Relocate all erk documentation from `.erk/docs/agent` to `docs/learned/` (c090e42d3)

### Added

- Add missing artifact detection to complement orphan detection for bidirectional artifact health checks (26d86f12a)
- Add doctor checks for exit-plan-hook and required-version validation (fa8abf494)
- Add erk-managed indicator badges to artifact list command output (36455b0c6)
- Add retry logic with exponential backoff to prompt executor for transient API failures (01aa33028)
- Add `impl` command alias for `implement` in shell integration (d7c9a4596)
- Establish `.erk/prompt-hooks/` directory for AI-readable hook instructions (049bca462)
- Add "Edit the plan" option to exit plan mode hook (d0ddc2889)
- Add `-f`/`--force` flag to `erk pr submit` for diverged branches (a8b46b01f)
- Add `show_hidden_commands` config option to control visibility of deprecated commands (91032b07d)
- Add hook initialization support to `erk init` command with `--hooks` flag (871bffe52)
- Add backup file creation when modifying settings.json (79c555d92)
- Add legacy pattern detection health checks for early dogfooders (d12366166)
- Add tool version checking to warn when installed erk is outdated (fa5b66ae4)
- Add automatic `--pull/--no-pull` option to `erk pr land` command (bce4d4bb4)
- Always show last commit time in branch list by default (6083f3d94)
- Add `reply-to-discussion-comment` exec command for formatted PR comment replies (74c66c420)
- Implement LLM-based step extraction for plan implementation folders (55aeb3bda)

### Changed

- Restrict artifact sync to only copy bundled items, preventing dev-only artifacts from leaking into projects (af8fa25c9)
- Make missing artifacts detection fail instead of warn (4f9cead04)
- Rename `/erk:save-plan` command to `/erk:plan-save` for consistency (becabfd1c)
- Integrate artifact syncing into `erk init` command (0130af179)
- Rename agent-docs skill to learned-docs (05f176b71)
- Flatten agent folders to top-level artifacts (0a15dabe2)
- Move `/gt:pr-submit` to `/erk:pr-submit`, from the gt kit to the erk kit
- Move erk scripts to top-level `erk exec` from `erk kit exec erk` (7b3c2b2fd)
- Remove kit registry subsystem (e77266b27)
- Remove `kit list`, `remove`, `search`, and `show` commands - consolidated into `dot-agent` (0ab9f47c6)
- Rename `auto_restack_skip_dangerous` config to `auto_restack_require_dangerous_flag` with flipped default (9785d6fd5)
- Convert devrun from kit to single agent file (8ad2729fc)
- Remove dignified-python kit - consolidated into vanilla skill (d3f19bc5d)
- Consolidate dignified-python skill into single version-aware implementation (a058a259f)
- Rename `gt-graphite` skill to `gt` with simplified directory structure (b6a2bb40b)
- Streamline devrun agent to use Sonnet model with minimal documentation (80d22f5d6)
- Standardize erk hook ID to `user-prompt-hook` via `erk exec` command (a3c876561)
- Rename health check names to kebab-case format (216e2a352)
- Scrub all kit references from repository (c444de13c)
- Remove support for standalone docs in `.claude/docs/` directory; use skills instead (753032a9a)
- Make PR parsing stricter by requiring github.com URLs (31a35a253)
- Eliminate kit.yaml manifest files, use frontmatter-based artifact discovery (8ab826ceb)
- Remove `erk kit` CLI commands and simplify artifact management (365c0032f)

### Fixed

- Fix missing error handling for deleted plan comment references with graceful fallback (37bbece52)
- Fix artifact check to display only installed artifacts instead of bundled defaults (02d8392b9)
- Fix artifact sync path detection for editable installs (9623b0c87)
- Fix function name import and call in post_plan_comment script (435c0bb09)
- Fix `erk stack list` to show branches without worktrees using ancestor worktree (bc6a308b0)
- Fix: Validate GitHub PR base branch matches local trunk before landing (3897eb658)
- Fix AskUserQuestion option formatting in exit plan mode hook (ff62f6ac0)
- Fix hook subdirectory bug by using shared scratch directory utilities (7da1528fc)
- Fix shell completion context creation in resilient parsing mode (b95821151)
- Re-implement branch divergence check for PR submission with pre-flight validation (eca895cf3)
- Fix LLM step extraction robustness by upgrading to Sonnet model (7c6d8eaca)
- Fix LLM empty output handling in step extraction with diagnostic logging (94875b0ba)
- Add issue title to plan save output (edfe76804)

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
