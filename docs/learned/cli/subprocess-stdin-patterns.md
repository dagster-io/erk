---
title: Subprocess Stdin Patterns
read_when:
  - "passing content to CLI tools via stdin"
  - "using subprocess with input parameter"
  - "CLI flags that only work with stdin"
---

# Subprocess Stdin Patterns

Patterns for using stdin with subprocess when CLI flags require it.

## When to Use stdin Instead of File Paths

Some CLI tools have flags that only work when reading from stdin. When you encounter this pattern, use subprocess `input` parameter instead of temp files.

### Pattern: stdin with subprocess.run

```python
# Instead of creating temp files:
result = subprocess.run(
    ["command", "-", "--flag", "value"],  # "-" indicates stdin
    input=content,                          # Pass content directly
    text=True,                              # Handle as text (not bytes)
    capture_output=True,
    check=True,
)
```

### Benefits

1. **No temp file cleanup**: Avoid tempfile management and cleanup
2. **No filename conflicts**: Temp files get random prefixes that may interfere with flags
3. **Simpler code**: One less resource to manage
4. **More portable**: No filesystem race conditions

### Example: gh gist create

```python
# gh gist create --filename only works with stdin
result = subprocess.run(
    ["gh", "gist", "create", "-", "--filename", filename, "--desc", description],
    input=content,
    text=True,
    capture_output=True,
    check=True,
)
gist_url = result.stdout.strip()
```

### Testing stdin-based Calls

When testing code that uses stdin, verify the input content was passed correctly. See `fake-driven-testing` skill for fake gateway patterns that capture subprocess calls.

## Related Topics

- [Subprocess Wrappers](../architecture/subprocess-wrappers.md) - General subprocess patterns
- [GitHub CLI Quirks](../architecture/github-cli-quirks.md) - gh gist create --filename behavior
