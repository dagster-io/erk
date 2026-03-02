# Fix: Skills not installed on wheel installs (`erk artifact sync`)

## Context

When users install erk 0.9.2 via wheel (not editable) and run `erk artifact sync`, the sync reports success ("Synced 30 artifact files") but `erk doctor` still shows 4-6 skills as "not-installed" or "changed-upstream". The root cause is a missing wheel packaging mapping in `pyproject.toml`.

## Root Cause

In `pyproject.toml` lines 67-79, all skills are force-included to `erk/data/codex/skills/` only:
```
".claude/skills/erk-exec" = "erk/data/codex/skills/erk-exec"
```

But there are **no entries** mapping skills to `erk/data/claude/skills/`.

The Claude sync path (`get_bundled_claude_dir()` in `src/erk/artifacts/paths.py:48`) returns `erk/data/claude/` for wheel installs. So `sync_artifacts` looks for skills at `erk/data/claude/skills/{name}/` — which doesn't exist in the wheel. The sync silently succeeds with 0 skill files because `_sync_directory_artifacts` (sync.py:211) returns early when `source_dir` doesn't exist.

Commands and agents are correctly mapped to `erk/data/claude/` — skills were only mapped to the codex path.

## Fix

Add force-include entries in `pyproject.toml` mapping each skill to `erk/data/claude/skills/` as well, matching the existing pattern for commands and agents.

### File: `pyproject.toml`

After the existing codex skills block (line 79), add a Claude skills block:

```toml
# Claude skills (same source files, needed by Claude Code sync path)
".claude/skills/cli-push-down" = "erk/data/claude/skills/cli-push-down"
".claude/skills/dignified-python" = "erk/data/claude/skills/dignified-python"
".claude/skills/fake-driven-testing" = "erk/data/claude/skills/fake-driven-testing"
".claude/skills/erk-diff-analysis" = "erk/data/claude/skills/erk-diff-analysis"
".claude/skills/erk-exec" = "erk/data/claude/skills/erk-exec"
".claude/skills/erk-planning" = "erk/data/claude/skills/erk-planning"
".claude/skills/objective" = "erk/data/claude/skills/objective"
".claude/skills/gh" = "erk/data/claude/skills/gh"
".claude/skills/gt" = "erk/data/claude/skills/gt"
".claude/skills/learned-docs" = "erk/data/claude/skills/learned-docs"
".claude/skills/dignified-code-simplifier" = "erk/data/claude/skills/dignified-code-simplifier"
".claude/skills/pr-operations" = "erk/data/claude/skills/pr-operations"
".claude/skills/pr-feedback-classifier" = "erk/data/claude/skills/pr-feedback-classifier"
```

## Verification

1. Build a wheel: `uv build`
2. Inspect wheel contents: `unzip -l dist/erk-*.whl | grep "data/claude/skills"`  — should show all 13 skills
3. Install in a test venv and run `erk artifact sync` + `erk doctor` — skills should show as up-to-date
