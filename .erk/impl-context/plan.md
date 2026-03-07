# Changelog Update + Remove Bundled Refactoring Skills

## Context

Two tasks after reviewing the changelog proposal:
1. Update CHANGELOG.md with approved entries (filtering out the refactoring skills entry)
2. Remove the `refac-module-to-subpackage` and `refac-cli-push-down` skills entirely — they shouldn't be bundled with erk

## Task 1: Update CHANGELOG.md

Add entries to the `## [Unreleased]` section with an "As of" marker set to `ad89cf1df`.

### Added (5)
- Add `erk pr prepare` command to set up impl-context independently from checkout (aa70e4d71)
- Add `erk reconcile` command to detect and clean up branches merged outside `erk land` (a35700ac4)
- Add `--from-current-branch` flag to `erk slot assign` (5b3edff2a)
- Fall back to Claude CLI for LLM calls when `ANTHROPIC_API_KEY` is unavailable (ad89cf1df)
- Add artifact allowlist to suppress `erk doctor` warnings for intentionally-modified artifacts (b01bd9e5f)

### Changed (1)
- Rename `erk pr reconcile-with-remote` to `erk pr diverge-fix` (a35700ac4)

### Fixed (5)
- Fix `erk pr teleport` not registering branch with Graphite for non-stacked PRs (9f617a62b)
- Fix Graphite divergence in `erk pr checkout` for stacked PRs by rebasing before Graphite tracking (aa70e4d71)
- Fix trunk sync leaving index out of date after `erk land`, causing staged reverse changes (13ab95a1e)
- Fix `erk doctor` hiding warnings behind green checkmarks in condensed mode (b01bd9e5f)
- Restore progress feedback ("Still waiting...") during PR description generation (e9ebcfe11)

## Task 2: Remove Refactoring Skills

Delete the skill files and remove all registry references.

### Files to delete
- `.claude/skills/refac-cli-push-down/SKILL.md` (and directory)
- `.claude/skills/refac-module-to-subpackage/SKILL.md` (and directory)

### Files to edit

1. **`src/erk/capabilities/skills/bundled.py`**
   - Line 24: Remove `"refac-module-to-subpackage"` from `_UNBUNDLED_SKILLS`
   - Line 47: Remove `"refac-cli-push-down": "Moving mechanical computation..."` from `bundled_skills()`

2. **`src/erk/core/capabilities/codex_portable.py`**
   - Line 18: Remove `"refac-cli-push-down"` from `codex_portable_skills()`

3. **`pyproject.toml`**
   - Line 67: Remove `".claude/skills/refac-cli-push-down" = "erk/data/claude/skills/refac-cli-push-down"`

4. **`docs/developer/agentic-engineering-patterns/README.md`**
   - Line 49: Remove or update the reference to `refac-cli-push-down` skill

## Verification

- Run `make fast-ci` to ensure no broken imports or test failures
- Grep for `refac-cli-push-down` and `refac-module-to-subpackage` to confirm no remaining references
