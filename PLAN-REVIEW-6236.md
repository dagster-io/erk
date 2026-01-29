# Plan: Compress docs/learned/index.md for Agent Consumption

## Context

Vercel's evals showed a compressed docs index (40KB → 8KB) in AGENTS.md achieved 100% agent pass rate. The key: agents need to know WHAT EXISTS and WHERE TO FIND IT, not read human-oriented prose.

Erk's `docs/learned/index.md` is embedded in AGENTS.md via `@` include (~3.2KB ambient context). It currently contains:

- Human-contributor instructions ("Add docs here for...") irrelevant to agents
- 13 of 25 categories with NO description (zero matching signal)
- A preamble that duplicates AGENTS.md's "Documentation-First Discovery" section
- Two separate dicts (`CATEGORY_DESCRIPTIONS` + `CATEGORY_ROUTING_HINTS`) with overlapping purpose

## Approach: Markdown-Based Category Keywords with Cached Loading

Move category keywords out of Python dicts and into a markdown file (`docs/learned/category-keywords.md`). This keeps documentation metadata in documentation, not code. The Python code loads and caches the parsed result via a `@cache`-decorated function.

Strip all human-oriented prose from descriptions. Add keywords for every category. Remove the redundant preamble from the generated index.

## Changes

### 1. Create `docs/learned/category-keywords.md`

**New file.** A markdown table that maps category names to terse keyword phrases. This replaces both `CATEGORY_DESCRIPTIONS` and `CATEGORY_ROUTING_HINTS` dicts.

```markdown
<!-- Source of truth for category keywords used in index and tripwires generation. -->
<!-- Edit this file, then run 'erk docs sync' to regenerate indexes. -->

# Category Keywords

| Category      | Keywords                                                        |
| ------------- | --------------------------------------------------------------- |
| architecture  | core patterns, dry-run, gateways, subprocess, shell integration |
| capabilities  | Claude Code capabilities, tool use                              |
| checklists    | step-by-step checklists, implementation guides                  |
| ci            | GitHub Actions, `.github/workflows/`, `.github/actions/`        |
| claude-code   | Claude Code configuration, settings                             |
| cli           | CLI commands, Click, output formatting, `src/erk/cli/`          |
| commands      | slash commands, `.claude/commands/`                             |
| config        | project configuration, settings files                           |
| configuration | erk configuration, YAML config                                  |
| documentation | doc structure, documentation methodology, agent docs            |
| erk           | erk workflows, worktrees, PR sync, Graphite                     |
| erk-dev       | erk development, internal tooling                               |
| gateway       | gateway implementations, `gateway/` code                        |
| hooks         | Claude hooks, `.claude/hooks/`                                  |
| integrations  | external integrations, third-party tools                        |
| objectives    | objectives, goal tracking                                       |
| planning      | plans, `.impl/`, `.worker-impl/`, agent delegation              |
| pr-operations | pull requests, PR workflows                                     |
| refactoring   | refactoring patterns, code restructuring                        |
| reference     | API specs, format specifications                                |
| sessions      | session logs, `~/.claude/projects/`, parallel sessions          |
| testing       | tests, test infrastructure, `tests/`                            |
| textual       | Textual framework                                               |
| tui           | TUI application, `src/erk/tui/`                                 |
| workflows     | workflow patterns, automation                                   |
```

This file is NOT auto-generated — it's a source-of-truth that humans edit. It should be excluded from the `discover_agent_docs()` scan (it has no frontmatter and is not a learned doc).

### 2. Replace two dicts with cached loader in operations.py

**File:** `src/erk/agent_docs/operations.py`

Delete `CATEGORY_DESCRIPTIONS` (lines 31-78) and `CATEGORY_ROUTING_HINTS` (lines 83-96). Replace with a `@cache`-decorated function that parses the markdown table:

```python
from functools import cache

@cache
def load_category_keywords(docs_root: Path) -> dict[str, str]:
    """Load category keywords from docs/learned/category-keywords.md.

    Parses the markdown table into a dict mapping category name to keywords.
    Cached for the lifetime of the process.
    """
    keywords_path = docs_root / "category-keywords.md"
    if not keywords_path.exists():
        return {}
    content = keywords_path.read_text(encoding="utf-8")
    result: dict[str, str] = {}
    for line in content.splitlines():
        if not line.startswith("| ") or line.startswith("| Category") or line.startswith("| ---"):
            continue
        parts = [p.strip() for p in line.split("|")]
        # parts: ['', category, keywords, '']
        if len(parts) >= 4 and parts[1] and parts[2]:
            result[parts[1]] = parts[2]
    return result
```

Note: `@cache` requires hashable args. `Path` is hashable, so this works. The function is called once per `erk docs sync` invocation and cached for the process lifetime.

### 3. Update `generate_root_index()` in operations.py

**File:** `src/erk/agent_docs/operations.py` (lines 518-567)

Changes:

- **Add `docs_root: Path` parameter** to the function signature (needed to load keywords).
- **Remove preamble**: Drop the "Before starting work..." lines — this instruction now lives in AGENTS.md's "Documentation-First Discovery" section.
- **Change title**: "Agent Documentation" → "Agent Documentation Index"
- **Use `load_category_keywords()`**: Replace `CATEGORY_DESCRIPTIONS.get(category.name)` with `load_category_keywords(docs_root).get(category.name)`.

### 4. Update `generate_tripwires_index()` in operations.py

**File:** `src/erk/agent_docs/operations.py` (line 460)

- **Add `docs_root: Path` parameter** to the function signature.
- Change `CATEGORY_ROUTING_HINTS.get(...)` → `load_category_keywords(docs_root).get(...)`.

### 5. Update callers of both generation functions

Update the call sites of `generate_root_index()` and `generate_tripwires_index()` to pass the `docs_root` path. This is likely in the `sync_agent_docs()` function which already has access to the docs root path.

### 6. Exclude `category-keywords.md` from doc discovery

In `discover_agent_docs()`, add `category-keywords.md` to the list of skipped files (alongside `index.md` and `tripwires.md`).

### 7. Regenerate and verify

Run `erk docs sync` to regenerate `docs/learned/index.md` and `docs/learned/tripwires-index.md`, then verify output.

## Expected Output

**Before:**

```markdown
# Agent Documentation

Before starting work, scan the read-when conditions below.
If your current task matches, read the linked document **before writing code**.

## Categories

- [architecture/](architecture/) — Explore when working on core patterns (dry-run, gateways, subprocess, shell integration). Add docs here for cross-cutting technical patterns.
- [capabilities/](capabilities/)
- [checklists/](checklists/)
```

**After:**

```markdown
# Agent Documentation Index

## Categories

- [architecture/](architecture/) — core patterns, dry-run, gateways, subprocess, shell integration
- [capabilities/](capabilities/) — Claude Code capabilities, tool use
- [checklists/](checklists/) — step-by-step checklists, implementation guides
```

Every category gets keywords. No prose. No preamble.

## What This Does NOT Change

- `@docs/learned/index.md` embed in AGENTS.md stays (this just changes what it contains)
- Per-category index files keep their current format (read-when conditions per doc)
- Uncategorized docs section format stays the same
- Tripwires generation logic stays the same (just uses the new dict name)

## Verification

1. `erk docs sync` regenerates cleanly
2. Read `docs/learned/index.md` — confirm compact format, all 25 categories with keywords
3. Read `docs/learned/tripwires-index.md` — confirm routing hints still render correctly
4. `make fast-ci` passes
