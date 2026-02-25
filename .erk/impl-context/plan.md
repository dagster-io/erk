# Plan: Objective Maintenance Tooling and Safety Guards

## Context

During a session rerendering objective comments from 5-column (Plan+PR) to 4-column (PR-only) format, several mechanical failures exposed gaps in the objective tooling:

1. **Data loss**: `gh api -f body=@file` wrote a literal file path instead of file contents, corrupting objective #7159's comment. GitHub has no comment edit history API, so the data was unrecoverable.
2. **No rerender CLI**: Rerendering a comment required ~60 lines of throwaway Python calling internal functions. Multiple import errors along the way.
3. **No staleness detection**: `erk objective check` validates structure but doesn't compare body YAML against comment state. Stale comments are invisible.
4. **Wrong schema from hand-crafting**: Objective #8149 was created with schema_version "2", `steps` instead of `nodes`, no `slug` — all because the agent bypassed `/erk:objective-create`.
5. **Import path guessing**: Three failed imports before finding `replace_metadata_block_in_body` in `core.py`.

## Steps

### 1. Add AGENTS.md tripwires for GitHub API mutations

Add two CRITICAL rules to AGENTS.md:

```
CRITICAL: When mutating GitHub issues or comments via `gh api`, NEVER use `-f body=@file`.
The `@` prefix does not read file contents with `-f` — it writes the literal string.
Use `--input <json-file>` with a JSON payload instead. Before mutating any GitHub comment,
save the original body to a local backup file — GitHub does not expose comment edit history.

CRITICAL: When creating an objective issue, ALWAYS use `/erk:objective-create`.
Never hand-craft the issue body — the roadmap schema (v4, nodes, slugs, <details> wrapper)
is complex enough that hand-crafting will produce invalid metadata.
```

### 2. Create `erk exec rerender-objective-comment` command

New exec script that:
- Takes `--issue <number>` or `--all` flag
- Fetches issue body YAML (source of truth) and comment body
- Calls `rerender_comment_roadmap()` to regenerate tables in current format
- Updates comment via GitHub API (using `--input` with JSON payload, not `-f body=@`)
- Reports what changed (old column count vs new, stale nodes)

Implementation:
- New file: `src/erk/cli/commands/exec/scripts/rerender_objective_comment.py`
- Register in exec group
- Uses existing `rerender_comment_roadmap()` from `roadmap.py`
- `--all` mode: fetches all open `erk-objective` issues, processes each
- `--dry-run` flag: shows what would change without mutating

### 3. Extend `erk objective check` with comment staleness detection

Add a new validation check to `check_cmd.py`:

- Parse body YAML nodes (source of truth)
- Parse comment YAML/tables (rendered view)
- Compare: status mismatches, column format (4-col vs 5-col), missing nodes
- Report as `[WARN] Comment roadmap is stale` (warning, not failure — staleness is cosmetic)

This turns the silent drift into visible signal.

### 4. Create metadata module API reference doc

New file: `docs/learned/architecture/metadata-module-api.md`

Quick-reference of the public API surface:
- `core.py`: block creation, parsing, extraction, replacement functions
- `roadmap.py`: node/phase types, parsing, rendering, mutation functions
- Import paths for each function

This prevents the "three failed imports" pattern.

### 5. Add `github-cli-limits.md` section on `-f` vs `--input`

Extend the existing `docs/learned/architecture/github-cli-limits.md` with a section documenting:
- `-f key=value` writes literal string values
- `-f key=@file` does NOT read file contents (common misconception)
- `--input file.json` reads file contents as the full request body
- When to use each

## Notes

- The rerender command should be idempotent — running it twice produces the same result
- `--all` mode should report a summary: "8 objectives checked, 6 rerendered, 2 already current"
- The staleness check in `erk objective check` should use `[WARN]` not `[FAIL]` since stale comments don't break functionality
- The backup-before-mutate pattern in step 1 is the highest-priority fix — it prevents future data loss
