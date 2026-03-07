# Changelog Update Plan

## Context
Updating CHANGELOG.md Unreleased section with 15 commits since 0.9.9 release (9caedc8c2..7d49225f8).

## Changes to CHANGELOG.md

Update the `## [Unreleased]` section (line 8) with the following entries and "As of" marker:

```markdown
## [Unreleased]

<!-- As of: 7d49225f8 -->

### Added

- Support running `erk one-shot --repo owner/repo` to dispatch tasks to remote repositories without a local git clone (c38a10fd, 83ba44ce, 70e592342)
- Codespace connect auto-checks out local branch in remote environment (9aa2d881)
- Add objective node management: update fields and add new nodes to existing phases (74f36b32)
- Wire incremental dispatch into TUI with plan input modal (e94dabcf)
- Hide stub branches from `erk br list` by default, with `--all/-a` flag to show them (578cc981)
- Make TUI help screen view-mode-aware, showing context-sensitive shortcuts for plans vs objectives (433c9c2e)

### Changed

- Show conflicted files and prompt for confirmation before launching Claude in `erk pr rebase` (c0461e8a)
- Sort command palette menu items alphabetically within each subgroup (94957ecb)

### Fixed

- Fix land learn pipeline to fetch remote sessions from async-learn branches when local sessions are missing (2db54844)
```

Existing content below (starting at `## [0.9.9]`) is preserved unchanged.
