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

## Step 1: Get PR Diff and Identify Changed Doc Files

Run `gh pr diff` and filter to `docs/learned/**/*.md` files in the PR.

For each changed doc file, read the full file content using the Read tool.

## Step 2: Extract Code Blocks from Changed/Added Lines

For each doc file, scan the diff for fenced code blocks that meet ALL these criteria:

- Are on `+` lines in the diff (new or modified content)
- Are delimited by triple backticks (```)
- Contain Python code (```python tag or untagged blocks with Python syntax)
- Are longer than 5 lines

Extract the code block content and line number range from the diff.

## Step 3: Check Each Code Block for Verbatim Source Matches

For each candidate code block extracted in Step 2, apply these heuristics to determine if it's a verbatim copy:

### 3a. erk Import Check

Does the block contain `from erk` or `import erk`? If yes, it references real project code and is a candidate for verbatim copy detection.

### 3b. Definition Extraction

Extract any `class Foo` or `def bar` names from the block using these patterns:

- `class ClassName(...):`
- `class ClassName:`
- `def function_name(...)`
- `def function_name(`

### 3c. Source Search

For each extracted class or function name, search the codebase:

1. Use Read tool to search in `src/erk/` and `packages/erk-shared/src/` for matching class/function definitions
2. Compare the code block content against the source file content (line-by-line)

### 3d. Match Criteria

A block is flagged as a verbatim copy if:

- **3+ consecutive lines match** a source file (ignoring leading/trailing whitespace and comments), OR
- **The block contains a complete class/function definition** that exists in source with matching structure

## Step 4: Classify Each Code Block

After checking in Step 3, classify each code block as:

- **Verbatim copy**: Real source code that will go stale. **Flag it** with an inline comment.
- **Pattern/template**: Uses made-up names (MyGateway, ExampleWidget, FooService) or shows a concept without matching real source. **Skip it**.
- **CLI/command example**: Shows bash commands, CLI output, or shell examples. **Skip it**.
- **Short snippet** (≤5 lines): Too small to matter. **Skip it**.

Only verbatim copies should be flagged.

## Step 5: Post Inline Comments

For each verbatim copy found in Step 4, post an inline comment at the start of the code block with this format:

```
**Learned Docs**: Verbatim source code copy detected.

Source: `<source_file_path>:<start_line>-<end_line>`

This code block copies ~N lines from the source file and will go stale if the source changes.

Suggested fix: Replace the code block with a source pointer:

> See `ClassName.method_name()` in `<relative_path>:<line>`.

If a short snippet is needed for context, keep it to ≤5 lines showing the key insight, with a pointer to the full source.
```

Example inline comment:

```
**Learned Docs**: Verbatim source code copy detected.

Source: `src/erk/gateway/git/git.py:45-62`

This code block copies ~18 lines from the source file and will go stale if the source changes.

Suggested fix: Replace the code block with a source pointer:

> See `Git.add()` in `src/erk/gateway/git/git.py:45`.

If a short snippet is needed for context, keep it to ≤5 lines showing the key insight, with a pointer to the full source.
```

## Step 6: Summary Comment Format

Post a summary comment with this format (preserve existing Activity Log entries and prepend new entry):

```
### Learned Docs Review

| File | Verbatim Blocks | Status |
|------|----------------|--------|
| `docs/learned/foo/bar.md` | 2 found | ❌ |
| `docs/learned/baz/qux.md` | 0 found | ✅ |

(Only list files that were checked. Use ✅ when no verbatim blocks found, ❌ when violations detected.)

### Activity Log
- [timestamp] Found 2 verbatim blocks (src/erk/foo.py in docs/learned/bar.md)
- [timestamp] All docs clean, no verbatim copies detected
- [timestamp] 1 verbatim block fixed, 0 remaining

(Keep last 10 entries maximum. Prepend new entry at the top.)
```

Activity log entry examples:

- "Found 2 verbatim blocks (src/erk/gateway/git/git.py in docs/learned/testing/testing.md)"
- "All docs clean, no verbatim copies detected"
- "1 verbatim block detected in docs/learned/architecture/subprocess-wrappers.md"
- "No changes to docs/learned/ in this PR"

Keep the last 10 log entries maximum.

## Key Design Notes

1. **Only check `+` lines in diff**: Don't flag pre-existing verbatim code in unchanged files. Only flag new/modified code blocks being added in the PR.

2. **5-line threshold**: Blocks ≤5 lines are acceptable as illustrative snippets even if they match source. The problem is large (10+ line) copied blocks.

3. **Pattern detection via name matching**: Extract class/function names and search for them in source. This is fast and catches the common case.

4. **Actionable comments**: Each comment includes the exact source path so a reviewer agent or human can immediately fix it without investigation.
