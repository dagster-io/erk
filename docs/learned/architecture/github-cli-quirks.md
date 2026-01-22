---
title: GitHub CLI Quirks and Edge Cases
read_when:
  - "using gh gist create with --filename flag"
  - "debugging unexpected gh CLI behavior"
  - "working with gh gist commands"
tripwires:
  - action: "using gh gist create with --filename flag"
    warning: "--filename only works with stdin input (-), not file paths."
---

# GitHub CLI Quirks and Edge Cases

Non-obvious behaviors in GitHub CLI that can cause subtle bugs.

## gh gist create --filename Flag

**The Issue**: The `--filename` flag only works when reading from stdin (`-`), NOT when providing a file path argument.

### Symptoms

When you run:

```bash
gh gist create /path/to/file --filename desired-name.txt
```

The `--filename` flag is silently ignored. The gist file inherits the original filename (e.g., `tmpXXXX_session.jsonl` if using tempfile).

### Root Cause

From `gh gist create --help`:

> `--filename string   Provide a filename to be used when reading from standard input`

The flag is explicitly scoped to stdin mode only.

### Broken Pattern

```python
# WRONG: --filename ignored for file paths
with tempfile.NamedTemporaryFile(suffix=f"_{filename}") as f:
    f.write(content)
    subprocess.run(["gh", "gist", "create", f.name, "--filename", "session.jsonl"])
# Result: gist created with "tmpXXXX_session.jsonl" filename
```

### Working Pattern

```python
# CORRECT: Use stdin with --filename
result = subprocess.run(
    ["gh", "gist", "create", "-", "--filename", "session.jsonl"],
    input=content,
    text=True,
    capture_output=True,
    check=True
)
# Result: gist created with "session.jsonl" filename
```

### Why This Matters

- Downstream code may construct URLs assuming a specific filename
- The mismatch causes 404 errors when accessing gist content
- The bug is silent - no warning when `--filename` is ignored

## Related Topics

- [GitHub Gist URL Patterns](github-gist-api.md) - URL construction for gist content
- [Subprocess Wrappers](subprocess-wrappers.md) - General subprocess patterns
