# Changelog

All notable changes to erk will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.0] - 2026-01-24 15:12 PT

### Release Overview

This release adds remote execution capabilities, plan replanning workflows, and numerous TUI improvements for managing plans and PRs.

#### GitHub Codespaces Integration

**What it solves:** Running Claude implementations locally can be resource-intensive and requires keeping your machine available.

**How it works:** Create and manage Codespaces that can execute Claude implementations remotely. Codespaces are provisioned with erk and Claude Code pre-configured.

**Key features:** `erk codespace setup`, `erk codespace connect`, `--codespace` flag for `erk implement` and `erk prepare`.

#### Remote PR Review Addressing

**What it solves:** Addressing PR review comments previously required checking out the branch locally.

**How it works:** Triggers GitHub Actions to run Claude in CI, which reads review comments, makes changes, and pushes commits.

**Key features:** `erk pr address-remote` command, available in TUI via command palette.

#### Plan Replanning

**What it solves:** Plans can become stale as the codebase evolves, requiring re-evaluation against current state.

**How it works:** Re-reads the original plan context and generates an updated implementation plan considering recent changes.

**Key features:** `erk plan replan` CLI command, TUI shortcut "6" for replanning selected plans.

#### Branch Sync Intelligence

**What it solves:** Diverged branches cause confusing errors during stack operations.

**How it works:** Detects divergence between local and remote branches, offering intelligent sync/rebase options.

**Key features:** `/erk:sync-divergence` command, automatic divergence detection in land and sync commands.

---

_The sections below document all changes since 0.6.0:_

### Added

- Add `erk pr address-remote` to TUI command palette
- Add Claude-generated summaries to PR comments for `pr-address` workflow
- Add workflow run URL backlink to plans created from GitHub Actions
- Add `erk pr address-remote` command to trigger PR review comment addressing via GitHub Actions
- Add `/erk:sync-divergence` command to resolve diverged branches with intelligent sync/rebase
- Add `-f/--force` flag to `erk plan submit` for non-interactive branch cleanup
- Add PR cache polling for immediate status line display after submit
- Add objective column to TUI plan table with click-to-open functionality
- Add branch reuse detection in `erk plan submit` with interactive prompt to reuse existing branches
- Add multi-plan consolidation support to `erk plan replan` command
- Add automatic trunk sync validation in `erk plan submit`
- Add `get-pr-commits` and `close-issue-with-comment` exec commands
- Add `pr-sync-commit` exec command to sync PR title/body from latest commit message
- Display all available config keys in `erk config list` including interactive_claude settings
- Add `erk plan replan` CLI command for re-evaluating existing plans
- Add replan option to TUI command menu with keyboard shortcut "6"
- Show workflow URL for in-progress learn status in `erk plan view`
- Add prepare-and-implement one-liner to plan save output
- Enhance `erk plan view` with branch inference and improved learn status display
- Add closed PR detection to slot diagnostics and repair
- Auto-detect objective from branch in `erk exec land-execute` command
- Add `--codespace` isolation mode to `erk prepare` and `erk branch create` commands
- Add GitHub Codespaces integration for remote Claude execution with `erk codespace` commands (setup, connect, list, remove, set-default) and `--codespace` flag for `erk implement`
- Add `erk objective close` command to close completed objective issues
- Add `--allow-dangerously-skip-permissions` flag support for interactive Claude config
- Add direnv configuration for automatic virtual environment setup

### Changed

- Improve Claude CLI error reporting with exit code, stderr, and stdout context
- Move `[erk-plan]` marker to start of PR titles for consistency with `[erk-learn]` format
- Replace text prefixes with emoji category indicators in TUI command palette
- Move `[erk-learn]` prefix to beginning of plan issue titles for improved visibility
- Learn workflow now runs automatically in CI after implementation instead of requiring `--async` flag
- `erk pr sync` now syncs and restacks already-tracked branches instead of exiting silently
- Detect diverged branches in land command and handle pull safely
- Fix Graphite branch tracking when parent branch diverged from remote
- GraphiteBranchManager now has GitHub fallback for PR lookups when branches aren't in Graphite cache
- Split `--codespace` into separate `--codespace` (boolean) and `--codespace-name` (string) options
- Add `--no-session-persistence` flag to Claude CLI invocations for session isolation
- Skip git push when Graphite handles PR submission
- Make erk hooks resilient to erk unavailability by gracefully exiting if erk is not in PATH
- Fix TUI land command to execute PR merge instead of just generating script

### Fixed

- Strip "Documentation Plan: " prefix from learn plan titles
- Fix `pr-address` workflow to detect unpushed commits before pushing
- Update PR title with `[no-changes]` prefix when implementation produces no code changes
- Fix TUI generating invalid "erk br co None" checkout commands for plans without worktrees
- Fix `erk plan list` not displaying `[erk-learn]` prefix in titles
- Fix TUI not displaying `[erk-learn]` prefix in plan titles
- Fix branch not visible in `gt ls` after `erk plan submit` due to stale Graphite cache
- Fix diverged local branches during Graphite stack operations with automatic force-update
- Fix learn-dispatch workflow with missing `--verbose` flag
- Fix `setup-impl-from-issue` to checkout newly created branch
- Fix `erk plan submit` to validate parent branch is tracked by Graphite before stacking
- Fix stale pool.json state handling in branch checkout and slot allocation
- Fix gist filename handling by using stdin input for `gh gist create`
- Fix `download-remote-session` gist URL handling for webpage URLs
- Fix `update_slot_objective` to create new slot entries (upsert behavior)
- Fix `.erk/bin/` description in `erk init` to say "generated shell scripts"

### Removed

- Remove `erk planner` command group and associated infrastructure

## [0.6.0] - 2026-01-20 07:57 PT

### Major Changes

- **Convention-based code review system**: Introduces automatic code review discovery and execution based on conventions. Capabilities can define review workflows that run automatically on PRs. Users benefit from consistent, automated review checks without manual configuration.

- **Clickable activation commands with clipboard support**: Activation commands now display as clickable OSC 8 hyperlinks and automatically copy to clipboard via OSC 52. `erk implement` now defaults to `--here` mode (in-place implementation) removing pool slot management. Users can click activation commands directly or paste from clipboard instead of manual copy-paste.

- **Shell integration removed**: The shell integration system (shell wrappers, automatic directory switching, ERK_SHELL env var) has been completely eliminated. Navigation commands now print activation script instructions instead of automatically switching directories. Users source activation scripts manually or use `cd`. This simplifies the architecture while keeping core erk functionality intact.

- **Remote conflict resolution workflow**: Added `erk pr fix-conflicts-remote` command to trigger AI-powered conflict resolution on GitHub Actions without checking out branches locally. Squashes commits, rebases onto base branch, and uses Claude to resolve conflicts. Available in TUI via "5" key.

### Added

- Add activation script generation when allocating worktree slots
- Add shell completion (bash/zsh) to worktree activation script
- Add `--local` mode to code review for pre-PR review execution
- Add Docker isolated implementation mode with filesystem isolation
- Add `-d` short flag alias to all `--dangerous` flags
- Add post-init prompt hook support for new developer setup
- Add clipboard copy support for shell integration message in land command
- Add `erk plan co` command for checking out plan branches with flexible identifier formats (plain numbers, P-prefixed, or URLs) and automatic worktree creation
- Add unresolved PR comment count column to `erk dash` TUI
- Add git index lock retry logic to prevent conflicts during concurrent worktree operations
- Add navigation guide for branches and worktrees documentation
- Add `erk prepare` command as shorthand for `erk br create --for-plan PLAN`
- Auto-detect plan number from branch name with `erk implement --here`
- Add `--for-plan` option to `erk br create` for creating branches directly from GitHub issues
- Add `objective_id` field to Plan dataclass for direct access to parent objectives
- Add "Fix Conflicts Remote" action to TUI dashboard with keyboard shortcut "5"

### Changed

- Sort capabilities list alphabetically by name
- Rename `/erk:system:impl-execute` command to `/erk:plan-implement`
- Simplify activation output when deleting branch with force flag
- Remove shell integration requirement from land command
- Always copy activation commands to clipboard
- Increase land action timeout to 10 minutes in TUI
- Show branch name in `erk plan view` output when implementation is active
- Expand implementation plan details blocks by default in GitHub issues
- Enable CI autofix agent to automatically fix type errors
- Remove `erk-plan` label from objectives, keeping only `erk-objective` for clearer distinction
- Simplify plan workflow to use `erk prepare` instead of three-mode `erk implement`
- Update PR checkout instructions to use shell script pattern for proper worktree activation
- Rewrite first-plan.md tutorial clarifying two-step workflow: `erk prepare` then `erk implement --here`
- Branch delete hint now only shown when `--force` flag is provided
- Land command now displays PR number and branch name in source command for transparency

### Fixed

- Fix duplicate activation output in `erk land --up` execute mode
- Fix land command confirmation prompts moved to execute phase
- Fix Graphite branch deletion to handle diverged branches correctly
- Fix child branch tracking in land operation by re-parenting in Graphite before merge
- Fix activation script output when landing without learning
- Fix learn prompt to require explicit confirmation before landing without learning
- Fix PR landing action to execute post-land callback in TUI
- Fix land command to output script path when landing from different directory
- Fix `erk-bootstrap` to distinguish between "not in project" and "erk not installed" with targeted error messages
- Fix artifact sync to respect installed capabilities when syncing workflows and actions
- Fix `--local` config to write to repo root instead of worktree, so config is shared across worktrees
- Fix `erk land` hanging on confirmation prompts in script mode
- Fix `--here` mode to use process replacement instead of subshell fallback
- Fix `land.sh` script sourcing with process substitution for reliable temp file handling
- Fix `land.sh` to use `source` instead of `eval`
- Remove redundant "Error: " prefix from `erk land` shell integration message
- Fix session preprocessing to correctly handle embedded `tool_result` blocks

### Removed

- Delete `erk-sh-bootstrap` package and related documentation

## [0.5.5] - 2026-01-15 06:53 PT

### Major Changes

- **Per-user local configuration**: Add `.erk/config.local.toml` for personal settings that override shared repo config. Configuration now supports three-level hierarchy (Global < Repo < Local) with `--repo` and `--local` flags for `erk config set`. The `config list` command shows source annotations like "(repo)" and "(local)" to clarify override origins.

### Added

- Add `--here` flag to `erk implement` for in-place implementation without worktree switching
- Add pre-flight validation for Graphite-tracked branches with clear remediation guidance
- Rename `plan get` to `plan view` with structured header metadata display and `--full` flag

### Changed

- Update PR submit Phase 1 message to say "Creating or Updating PR" for clarity
- Add `.erk/config.local.toml` to gitignore and health checks

### Fixed

- Fix FileNotFoundError when invoking erk from shell integration in venv environments
- Fix `erk pr sync` failure for stacked PRs with locally restacked parents
- Fix automatic Graphite branch tracking during worktree creation when Graphite is enabled
- Fix `erk doctor` to show remediation steps for artifact warnings, not just failures
- Fix `erk artifact sync` to update hook commands in settings.json, ensuring hooks stay current across erk versions
- Fix `erk pr land` learn prompt to default to continuing (press Enter to proceed)

## [0.5.4] - 2026-01-13 12:29 PT

### Added

- Add composite action extension point for customizing erk-impl workflow (Python version, system dependencies, environment variables)

### Changed

- Add secret validation to erk-impl workflow with clear error messages when ERK_QUEUE_GH_PAT is missing

### Fixed

- Fix `erk init` skipping global config creation when repo already erkified
- Fix erk-impl workflow silent failure on implementation errors
- Fix spurious learn warning when landing remote PRs without local worktrees

### Removed

- Remove `erk upgrade` command (version management now handled via `uv tool`)

## [0.5.3] - 2026-01-13 06:04 PT

### Major Changes

- **Shell integration bootstrap system**: Introduce `erk-sh-bootstrap`, a lightweight package that enables running erk via `uvx erk-sh-bootstrap` without requiring a global installation. Shell wrappers now delegate to project-local erk binaries, improving per-project version isolation.

### Added

- Add `--max-tokens` option to `preprocess-session` for automatic chunking of large session logs into multiple files
- Add `--dangerous` flag to `erk learn` command for skipping permission prompts

### Fixed

- Fix child PRs being auto-closed when landing parent branch by querying GitHub directly for dependent PRs
- Fix `erk submit` to track branches with Graphite, enabling proper PR stacking and preventing auto-closure of dependent PRs
- Fix hook updates not applying when hooks are re-installed (old hooks with stale commands now get replaced)
- Fix dignified-python-review capability workflow to use centralized Claude Code setup action

## [0.5.2] - 2026-01-12 07:54 PT

### Added

- Add `erk init capability remove` command for uninstalling capabilities
- Add `prompt_learn_on_land` config setting to disable learn prompts during PR landing

### Changed

- Make artifact health checks capability-aware to avoid false warnings for uninstalled capabilities

## [0.5.1] - 2026-01-12 01:42 PT

### Added

- Add learn event tracking to plan-header metadata for better session-plan correlation
- Add `-f` flag to TUI land PR commands for non-interactive mode

### Fixed

- Fix preprocess-session to filter agent logs by session ID, reducing output bloat
- Fix closing reference preservation when `.impl/issue.json` is missing
- Fix GitHub Actions code injection vulnerability in learn-dispatch workflow

## [0.5.0] - 2026-01-11 23:58 PT

### Release Overview

The 0.5.0 release consolidates four major systems that transform erk from a plan execution tool into a comprehensive platform for AI-assisted software engineering.

#### Objective System

Erk plans solve the single-PR problem well, but real engineering work often spans multiple related PRs toward a coherent goal. The Objective System provides coordination infrastructure for multi-PR initiatives.

**What it solves:** Context loss between related implementations. When work spans multiple sessions and PRs, design decisions, lessons learned, and progress tracking were previously scattered or lost entirely.

**How it works:** An objective is a GitHub issue (labeled `erk-objective`) that acts as a coordination document and changelog. It contains a phased roadmap breaking work into shippable PRs, design decisions that guide all related work, and action comments that capture lessons learned as each piece lands. Objectives can be completeable –– a defined set of substeps or phases –– or a permanent objective, that can be continuously evaluated against a system for all of time (e.g. ensure all files are less than 20k tokens).

**Key workflow:**

- `erk objective create` - Interactive creation with structure recommendations (steelthread-first development)
- `erk objective next-plan` - Pick a roadmap step and generate an implementation plan
- `erk land` integration - Automatically prompts to update objectives when landing related PRs

Objectives are human-first markdown documents optimized for session handoff—any future session can pick up implementation without re-exploring context.

#### Learning System

AI agents discover valuable insights during implementation: API quirks, architectural patterns, edge cases, and design rationale. This knowledge typically evaporates once the PR lands. The Learning System systematically captures and codifies these discoveries.

**What it solves:** Knowledge loss from implementation sessions. Claude reads files, discovers patterns, encounters gotchas, and makes decisions—but none of this persists beyond the session.

**How it works:** `erk learn` discovers all Claude Code sessions associated with a plan (planning session, implementation sessions) and launches Claude to analyze them. The `/erk:learn` skill performs deep session analysis, extracting documentation items that fill genuine knowledge gaps rather than duplicating existing documentation.

**Key features:**

- Session discovery from GitHub metadata and local logs
- Compressed XML preprocessing for efficient context
- Categorization: Learning gaps (external knowledge) vs Teaching gaps (documenting new features)
- Automated workflow via `learn-workflow` capability for hands-off documentation generation

The system creates a virtuous cycle: each implementation makes future implementations faster through accumulated documentation.

#### Capability-Based Architecture

As erk's feature set grew, initialization became unwieldy—a monolithic process that installed everything or nothing. The Capability System introduces modular, pluggable optional features.

**What it solves:** All-or-nothing feature installation. Different repositories need different features: some want code review workflows, others want the statusline, some want reminder systems. Previously this required manual file management.

**How it works:** Each capability is a self-contained unit with declarative installation, dependency checking, and status tracking. Capabilities span multiple types: skills, workflows, agents, reminders, and infrastructure settings. They can be project-scoped (per-repository) or user-scoped (global).

**Key commands:**

- `erk init capability list` - Show all available capabilities
- `erk init capability check` - Verify installation status
- `erk init capability add <name>` - Install one or more capabilities

Available capabilities include `dignified-python`, `fake-driven-testing`, `dignified-review`, `learn-workflow`, `statusline`, `shell-integration`, and reminder systems for coding standards enforcement.

#### Worktree Pool System

Git worktrees enable parallel development, but naive worktree management caused significant problems: slow creation, `index.lock` race conditions, shell state contamination, and unbounded resource consumption.

**What it solves:** The pool system addresses performance (worktree creation is slow), resource management (worktrees accumulating on disk), `index.lock` contention (concurrent git operations conflicting), and shell state isolation (clean separation of session artifacts).

**How it works:** Instead of creating and destroying worktrees on-demand, erk maintains a configurable pool of pre-allocated slots (`erk-slot-01` through `erk-slot-04` by default). Branches are assigned to slots dynamically, with LRU eviction when the pool is full. Placeholder branches hold unassigned slots ready for instant reuse.

**Key commands:**

- `erk slot init-pool` - Pre-allocate all slots
- `erk slot list` - Unified pool health view (assignments, status, issues)
- `erk slot repair` - Auto-fix stale assignments and orphaned state

The system includes comprehensive diagnostics detecting orphaned state, missing branches, and branch mismatches, with automatic repair capabilities.

---

In this specific version:

### Added

- Add `--no-delete` flag to `erk land` to preserve branch and worktree slot after merging PR
- Add `-f/--force` hint to error message when deleting branch with open PR
- Add `learn-workflow` as installable capability via `erk init capability add learn-workflow`
- Add opt-in reminder system for coding standards enforcement via capability markers in `.erk/state.toml`
- Add configurable Claude CLI launcher with `[interactive-claude]` config section for model, permission mode, and other settings
- Expand tutorial and topic documentation with installation guides and design explanations

### Changed

- Suppress slot warning when `--force` flag is specified in land command

### Fixed

- Fix `erk dash -l` hanging by setting subprocess stdin to DEVNULL
- Fix token reduction metric in session preprocessing to include agent logs in calculation
- Fix `erk land` failing when branch is checked out in stale pool state
- Skip dirty slots in `find_inactive_slot()` instead of failing, enabling concurrent slot allocation

### Removed

- Remove `erk plan start` command

## [0.4.7] - 2026-01-11 02:19 PT

### Major Changes

- **Shell integration is now optional**: `erk implement` works without shell integration configured. When ERK_SHELL is not set, erk spawns a subshell in the worktree and launches Claude automatically.
- **Simplified worktree preservation in `erk land`**: The command now always preserves slot worktrees when landing PRs, only deleting the branch. This prevents accidental worktree loss and makes the workflow more predictable for users with persistent worktree setups.
- **Reorganized init process into capabilities**: The init command now uses a capability-based architecture with `erk init capability` subcommands. Capabilities can be managed at project or user scope, and include skills, workflows, agents, and groups.

### Added

- Add PR review thread counts to statusline
- Add tripwires-review as an installable capability
- Add ShellIntegrationCapability for shell wrapper installation
- Add sync status display to branch and PR checkout commands showing ahead/behind/diverged state with bot commit detection
- Add ruff auto-format capability for automatic Python formatting on Write/Edit
- Add "Exists" column to `erk slot list` showing physical worktree directory status
- Add error message when submitting stacked PR without parent PR, guiding users to `gt submit -s`
- Offer to close plan issues missing closing references during `erk land`
- Add `erk admin test-erk-impl-gh-workflow` command for testing workflow changes before merge
- Validate Claude credentials in erk-impl workflow before execution
- Add Anthropic API authentication secret health check to `erk doctor`
- Add conditional erk-shared installation for monorepo flexibility
- Add `--dry-run` flag to `erk slot repair` for previewing repairs; repair now automatically fixes all four issue types
- Add branch context header to plan mode exit prompt
- Render plan content as Markdown in TUI dashboard
- Add `v` key binding to view full plan text in modal in TUI
- Add slot allocation support to `erk branch checkout` command
- Add slot allocation support to `erk pr checkout` with `--no-slot` and `--force` options
- Add health check for legacy slot naming convention in `erk doctor`
- Make `erk pr sync` work without Graphite using git-only mode
- Add automatic PS1 prompt modification for worktree subshells
- Fail on unresolved comments in non-interactive mode for `erk land`

### Changed

- Improve capability list formatting with scope grouping
- Refactor capability check output formatting
- Replace `--statusline` and `--with-dignified-review` flags with `erk init capability add` commands
- Graphite branch delete now falls back to git when branch is untracked or diverged
- Improve capability display formatting in init command output
- Support `erk land` without Graphite enabled
- Migrate diff extraction from GitHub API to local git to handle large diffs exceeding GitHub's ~20k line limit
- Fix PR submit output to distinguish between created and existing PRs
- Default to Yes for `erk init` settings confirmation
- Update TUI checkout command to use branch-based checkout
- Standardize "slot" terminology for worktree pool throughout CLI

### Fixed

- Fix false branch-mismatch error for stacked branches in slot list
- Fix index.lock race condition in erk land
- Fix CI autofix prompt variable substitution
- Fix statusline crash when creating RealGitHub instances without repo_info
- Fix GitHub integration by properly resolving Graphite implementation based on config
- Improve plan issue closure detection with retry logic and closing reference validation
- Fix `erk land` failing from non-slot worktrees by checking out trunk before branch deletion
- Fix `erk land` to preserve slot worktrees when branches are checked out via `gt get`
- Fix slot detection in `erk land` to use branch name instead of path comparison
- Fix actions bundling to be optional when workflows aren't installed
- Fix PR column in `erk wt ls` by using GitHub API instead of Graphite cache
- Make `erk dash` resilient to GitHub API failures
- Allow landing PRs for locally existing branches in TUI
- Fix `erk land -f` to execute objective update
- Fix version warning to use LBYL pattern for git repo detection

### Removed

- Remove `erk slot check` command; functionality merged into `erk slot repair`
- Remove `show_pr_info` configuration flag; PR info now always fetched efficiently
- Delete presets feature from init command

## [0.4.6] - 2026-01-06 12:21 PT

### Added

- Add `erk branch delete` command with worktree-aware cleanup
- Add HTTP client gateway for faster in-process plan closing in TUI
- Add prompt to close open PR when deleting branch
- Add 30-second timeout for streaming commands in TUI
- Update upstack PR base branches to trunk when landing stacked PRs
- Add MkDocs documentation build with GitHub Pages deployment
- Bundle GitHub Actions and CI autofix prompt in package distribution for external repo erk-impl support
- Add `erk doctor` health check for ERK_QUEUE_GH_PAT secret configuration

### Changed

- Restructure README into comprehensive documentation hub in `docs/`

## [0.4.5] - 2026-01-05 17:19 PT

### Changed

- `erk init` now sets up plans repo labels and Claude permissions automatically

### Fixed

- Fix submit command to use trunk as base when on placeholder or unpushed branches
- Handle `gh api` target repo substitution and validate erk-managed repos
- Handle terminal editors (vim, nano, etc.) in plan edit flow
- Silence version check warning outside git repos

## [0.4.4] - 2026-01-05 10:45 PT

### Added

- Add `--clear-hook-logs` option to `erk doctor` command
- Add check counts to status line display
- Add logging to statusline for debugging GitHub data fetches and cache behavior

### Changed

- Handle merge conflicts in erk-impl workflow by attempting rebase with Claude assistance
- Clarify plan-save command output handling to preserve dangerous option in instructions

### Fixed

- Fix keyword argument passing to create_branch_manager factory function

## [0.4.3] - 2026-01-05 07:55 PT

### Added

- Add `erk upgrade` command to update local installation to repo's required version
- Display plan issue closure status after landing PR
- Display plan title and file path in exit plan mode prompt for better context

### Changed

- Handle restack conflicts gracefully in `pr sync` with user-friendly guidance
- Prioritize Claude Code `/erk:plan-submit` slash command in plan submission next steps
- Condense `erk doctor` output with collapsible sub-groups and opt-in `--dogfooder` flag

## [0.4.2] - 2026-01-04 21:19 PT

### Added

- Add Python 3.11 support and fix forward reference compatibility

### Changed

- Implement always gets new slot for maximum parallelism

### Fixed

- Fix CI to use correct Python version in uv during unit tests

## [0.4.1] - 2026-01-04 19:40 PT

### Added

- Add `erk admin upgrade-repo` command to update repo to installed erk version
- Add `erk doctor` check for post-plan-implement CI hook configuration

### Fixed

- Fix orphaned worktree discovery to use git instead of pool state
- Fix branch creation with `--force` to reuse existing slots via checkout
- Fix hook state tracking to record all installed hooks in `erk sync`

## [0.4.0] - 2026-01-04 18:09 PT

### Major Changes

- **Worktree Pool System**: Pre-initialized worktree slots replace ephemeral worktree creation. Creating and deleting worktrees on larger repositories caused significant problems: shells left on deleted working directories, an epidemic of git `index.lock` issues, and slow worktree operations. The pool system maintains a configurable number of persistent slots that are reused across assignments. Commands: `erk slot init`, `erk slot list`, and `erk slot repair`.

- **`erk br` namespace for branch management**: Consolidated branch lifecycle commands (`create`, `assign`, `unassign`) under `erk br` (short alias for `branch`). The `slot` group now focuses exclusively on pool infrastructure. Includes `--no-slot` flag for creating branches without slot assignment.

- **`erk pr fix-conflicts` command**: AI-powered merge conflict resolution. When rebasing causes conflicts, this command uses Claude to analyze and resolve conflicts automatically.

### Added

- Detect uncommitted changes before checkout in slot assignment with user-friendly error messages
- Add `erk slot repair` command to remove stale assignments from pool state
- Create `/erk:implement-stacked-plan` command for stacked branch implementation
- Add visible URL column to objective list command output
- Add `pool.max_slots` configuration and worktree slot pre-initialization
- Add same-slot stacking for `erk implement` - stacks new branches on current branch instead of consuming a new slot
- Add "Changes" column to `erk slot list` showing dirty/clean status for each worktree
- Add `--dry-run` flag to `erk land` command to preview deletions without executing
- Bundle `dignified-python` skill with `erk sync` command by default

### Changed

- Clarify slot list UX with improved status ("available", "assigned", "error") and reason terminology
- Simplify slot unassign to accept only worktree names
- Rename objective plan creation command from `objective-create-plan` to `objective-next-plan`
- Rename pooled sync to pooled check
- Use `gt create` for branch creation when Graphite enabled
- Update CI workflows to use claude-haiku-4 instead of claude-opus-4-5

### Fixed

- Fix erk land UX issues: improve confirmation prompt clarity and prevent unwanted navigation
- Fix erk land to properly unassign pool slots instead of deleting them
- Fix pool_size config override when loading existing pool state
- Fix pooled implement shell integration registration
- Fix pooled unassign to checkout placeholder branch and validate worktree state
- Fix `erk pr land` failing when deleting remote branches from git worktrees
- Fix UserPromptSubmit hook matcher to apply to all prompts
- Fix delete remote branch for landing PRs via gh pr merge --delete-branch
- Suppress "branch not found" message during fork PR cleanup
- Fix erk land objective update flow and shell integration output routing
- Fix statusline detection to accept commands with or without uvx prefix
- Fix CLI crash when running outside git repository
- Fix slot selection to exclude initialized worktrees during on-demand creation

### Removed

- Delete auto-restack feature and related infrastructure
- Delete 9 dead erk exec commands
- Remove step progress tracking from implementation system - plans no longer require step metadata

## [0.3.3] - 2026-01-02 13:44 PT

### Changed

- Move erk-statusline from dev to core dependencies

### Fixed

- Fix BranchMetadata forward reference

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
