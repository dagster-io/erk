# Plan: Create Learned Docs Review for Verbatim Code Detection

## Goal

Create a new reviewer at `.github/reviews/learned-docs.md` that detects verbatim source code copies in `docs/learned/` markdown files and leaves actionable inline comments with enough context for a reviewer agent to apply fixes.

## What We're Building

A single file: `.github/reviews/learned-docs.md`

This reviewer triggers on PRs that touch `docs/learned/**/*.md` and checks each changed doc file for code blocks that are verbatim copies of project source code. When found, it leaves an inline comment with:
- The specific code block that's a verbatim copy
- The source file path and line numbers where the canonical code lives
- A suggested replacement (pointer to source instead of inline code)

## Review File Structure

### Frontmatter

```yaml
---
name: Learned Docs Review
paths:
  - "docs/learned/**/*.md"
marker: "<!-- learned-docs-review -->"
model: claude-haiku-4-5
timeout_minutes: 30
allowed_tools: "Bash(gh:*),Bash(erk exec:*),Read(*)"
enabled: true
---
```

### Detection Algorithm (Step-by-step instructions for the reviewer agent)

**Step 1: Get the diff and identify changed doc files**

Run `gh pr diff` and filter to `docs/learned/**/*.md` files. For each changed file, read the full file content.

**Step 2: Extract code blocks from changed/added lines**

For each doc file, find all fenced code blocks (``` delimited) that:
- Are on `+` lines in the diff (new or modified content)
- Contain Python code (```python or untagged blocks with Python syntax)
- Are longer than 5 lines

**Step 3: Check each code block for verbatim source matches**

For each candidate code block, apply these heuristics to determine if it's a verbatim copy:

1. **erk import check**: Does the block contain `from erk` or `import erk`? If yes, it references real project code.
2. **Definition extraction**: Extract any `class Foo` or `def bar` names from the block.
3. **Source search**: For each extracted name, search the codebase:
   - Use `Read` to search in `src/erk/` and `packages/erk-shared/src/` for matching class/function definitions
   - Compare the code block content against the source file content
4. **Match criteria**: A block is a verbatim copy if:
   - 3+ consecutive lines match a source file (ignoring whitespace/comments)
   - OR the block contains a complete class/function definition that exists in source

**Step 4: Classify each code block**

- **Verbatim copy**: Real source code that will go stale. Flag it.
- **Pattern/template**: Uses made-up names (MyGateway, ExampleWidget) or shows a concept without matching real source. Skip it.
- **CLI/command example**: Shows bash commands or CLI output. Skip it.
- **Short snippet** (<=5 lines): Too small to matter. Skip it.

**Step 5: Post inline comments**

For each verbatim copy found, post an inline comment at the start of the code block with this format:

```
**Learned Docs**: Verbatim source code copy detected.

Source: `<source_file_path>:<start_line>-<end_line>`

This code block copies ~N lines from the source file and will go stale if the source changes.

Suggested fix: Replace the code block with a source pointer:

> See `ClassName.method_name()` in `<relative_path>:<line>`.

If a short snippet is needed for context, keep it to ≤5 lines showing the key insight, with a pointer to the full source.
```

**Step 6: Summary comment**

```
### Learned Docs Review

| File | Verbatim Blocks | Status |
|------|----------------|--------|
| `docs/learned/foo/bar.md` | 2 found | ❌ |
| `docs/learned/baz/qux.md` | 0 found | ✅ |
```

Activity log: Keep last 10 entries.

## Key Design Decisions

1. **Only check `+` lines in diff**: Don't flag pre-existing verbatim code in unchanged files. Only flag new/modified code blocks being added in the PR.

2. **5-line threshold**: Blocks ≤5 lines are acceptable as illustrative snippets even if they match source. The problem is large (10+ line) copied blocks.

3. **Pattern detection via name matching**: Rather than doing expensive line-by-line diffing, extract class/function names and search for them in source. This is fast and catches the common case.

4. **Actionable comments**: Each comment includes the exact source path so a reviewer agent or human can immediately fix it without investigation.

## Files to Create/Modify

| File | Action |
|------|--------|
| `.github/reviews/learned-docs.md` | **Create** — the new review definition |

## Verification

1. Read the created file and confirm frontmatter is valid YAML
2. Confirm `paths` pattern matches `docs/learned/**/*.md` files
3. Confirm `marker` is unique (not used by other reviews)
4. Confirm `allowed_tools` includes `Read(*)` (needed to search source files)
5. Spot-check by mentally running the algorithm against a known verbatim copy (e.g., `testing/testing.md` with FakeGit constructor)