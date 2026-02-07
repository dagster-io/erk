---
name: code-diff-analyzer
description: Analyze PR diff to identify documentation needs for new code
allowed-tools:
  - Bash
  - Read
  - Glob
  - Grep
---

# Code Diff Analyzer Agent

Analyze a PR's changes to identify what was built and what needs documentation.

## Input

You receive:

- `pr_number`: The PR number to analyze
- `issue_number`: The parent plan issue number

## Analysis Process

1. **Fetch PR metadata:**

   ```bash
   gh pr view <pr_number> --json files,additions,deletions,title,body
   ```

2. **Get the diff (with large-PR fallback):**

   Try `gh pr diff` first. On failure (HTTP 406 or non-zero exit), fall back to the paginated REST API.

   ```bash
   # Try full diff first (works for most PRs)
   gh pr diff <pr_number>
   ```

   **If this fails** (HTTP 406 for PRs with 300+ files), use the REST API with pagination:

   ```bash
   gh api --paginate "repos/{owner}/{repo}/pulls/<pr_number>/files"
   ```

   This returns JSON with `filename`, `status`, `additions`, `deletions`, and `patch` per file. The `patch` field contains the per-file diff. For files with empty or truncated patches, read the actual file from the working tree to determine what was added (new functions, classes, etc.).

   Reference: `docs/learned/architecture/github-cli-limits.md` documents this limitation.

3. **Create inventory of what was built:**
   - New files created
   - New functions/classes added
   - New CLI commands (@click.command decorators)
   - New gateway methods (ABC additions)
   - New exec scripts
   - Config changes
   - Source locations for documentation pointers: for each item, note file path and key identifiers (class/function names) so agents can grep to find them

4. **For each inventory item, assess documentation need:**
   - Does this need docs? (Almost always yes for new features)
   - Where should docs go? (docs/learned/{category}/, tripwires.md, etc.)
   - What should be documented? (Usage, context, gotchas)

## Output Format

```
PR: #<number>
TITLE: <title>
STATS: +<additions> -<deletions> files: <count>

## Inventory

### New Files
| Path | Type | Documentation Needed | Location |
|------|------|---------------------|----------|
| ...  | ...  | Yes/No              | ...      |

### New Functions/Classes
| Name | File | Documentation Needed | Location |
|------|------|---------------------|----------|
| ...  | ...  | Yes/No              | ...      |

### New CLI Commands
| Command | File | Documentation Needed |
|---------|------|---------------------|
| ...     | ...  | Yes                 |

### New Gateway Methods
| Method | ABC | Documentation Needed |
|--------|-----|---------------------|
| ...    | ... | Tripwire (5 places) |

### Config Changes
| Change | Impact | Documentation Needed |
|--------|--------|---------------------|
| ...    | ...    | ...                 |

## Documentation Summary

Total items: <N>
Need documentation: <N>
Skip documentation: <N> (with reasons)

## Recommended Documentation Items

1. **<item>** → <location>: <what to document> (source: path/to/file.py, grep for ClassName/function_name)
2. ...

## Source Pointer Awareness

Every inventory item MUST include the source file path. This enables downstream agents to create documentation with source pointers instead of verbatim code blocks.

For each new function, class, CLI command, or gateway method, note:
- Full file path (e.g., `src/erk/planning/plan_manager.py`)
- Key identifiers (class name, function name) so agents can grep to locate the relevant code

See `docs/learned/documentation/source-pointers.md` for the two-part pattern used in documentation.
```

Note: "Self-documenting code" is NOT a valid reason to skip. Document context, not just code.
