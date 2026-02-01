---
title: Bash-Python Integration Patterns
read_when:
  - writing Python code in bash heredocs, generating complex regex patterns in bash hooks, debugging escaping issues in bash-to-Python transitions
---

# Bash-Python Integration Patterns

Erk hooks and scripts frequently generate Python code dynamically within bash heredocs. This creates escaping challenges when the Python code contains strings, regex patterns, or special characters.

## The Escaping Challenge

When writing Python inside bash heredocs, you encounter multiple layers of escaping:

1. **Bash string interpretation** — Variables like `$var` are expanded unless properly quoted
2. **Heredoc delimiter interpretation** — Single-quoted heredocs (`<<'EOF'`) prevent expansion, double-quoted allow it
3. **Python string escaping** — Python requires `\` escaping for regex special characters
4. **Regex metacharacters** — Patterns like `\s`, `\d`, `\w` need proper escaping through all layers

## Problem Pattern: Regex in Bash Heredocs

Complex regex patterns in Python strings require careful escaping to survive bash processing.

### Example: Import Alias Detection Regex

**The Goal**: Detect `import X as Y` where `X != Y` (aliasing violation)

**Python Pattern**: `r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'`

This pattern uses:

- `\s` for whitespace
- `\w` for word characters
- `(?!\1\b)` negative lookahead (reject re-export pattern `import X as X`)

**Bash Heredoc Challenge**: Writing this in a bash string requires escaping cascades:

```bash
# WRONG: Bash expands \s, \w, \1
cat <<EOF
import re
pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
EOF
# Result: Python receives malformed pattern (bash ate the backslashes)

# RIGHT: Use single-quoted heredoc to prevent bash expansion
cat <<'EOF'
import re
pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
EOF
# Result: Python receives literal string exactly as written
```

## Safe Pattern: Single-Quoted Heredocs

**Rule**: When generating Python code with regex patterns, **always use single-quoted heredocs** (`<<'EOF'`).

| Heredoc Style | Bash Expansion                | Use When                                                   |
| ------------- | ----------------------------- | ---------------------------------------------------------- |
| `<<EOF`       | ✅ Expands `$var`, `\n`, etc. | Need bash variable interpolation                           |
| `<<'EOF'`     | ❌ Literal (no expansion)     | Writing regex, Python raw strings, or code with `$` or `\` |

## Concrete Example: Pre-Commit Hook

**Context**: Pre-commit hook generates Python script to check for import aliases.

**Wrong Approach** (double-quoted heredoc):

```bash
cat <<EOF > /tmp/check_imports.py
import re
pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'  # Bash will mangle this
matches = re.findall(pattern, content)
EOF
```

**Right Approach** (single-quoted heredoc):

```bash
cat <<'EOF' > /tmp/check_imports.py
import re
pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'  # Survives bash unchanged
matches = re.findall(pattern, content)
EOF
```

## Hybrid Pattern: Partial Interpolation

**Problem**: Need to pass bash variables into Python code that also contains regex patterns.

**Solution**: Use double-quoted heredoc with selective escaping:

```bash
FILE_PATH="/path/to/file.py"

cat <<EOF > /tmp/check_imports.py
import re

# Bash variable interpolated here
file_path = "$FILE_PATH"

# Escape backslashes for regex pattern
pattern = r'^\\s*import\\s+(\\w+)\\s+as\\s+(?!\\1\\b)\\w+\\s*\$'

with open(file_path) as f:
    content = f.read()
    matches = re.findall(pattern, content, re.MULTILINE)
EOF
```

**Downside**: Every backslash in the regex must be doubled (`\\s` instead of `\s`), making patterns harder to read.

**Alternative**: Split into two stages:

```bash
# Stage 1: Generate template with placeholder
cat <<'EOF' > /tmp/check_imports.py.template
import re
pattern = r'^\s*import\s+(\w+)\s+as\s+(?!\1\b)\w+\s*$'
file_path = "PLACEHOLDER"
with open(file_path) as f:
    matches = re.findall(pattern, f.read(), re.MULTILINE)
EOF

# Stage 2: Replace placeholder with actual value
sed "s|PLACEHOLDER|$FILE_PATH|g" /tmp/check_imports.py.template > /tmp/check_imports.py
```

This keeps the regex pattern clean and readable.

## Recommendations

1. **Default to single-quoted heredocs** (`<<'EOF'`) for generated Python code
2. **Use placeholders + sed** when you need variable interpolation alongside complex patterns
3. **Avoid double-quoted heredocs with manual escaping** — they're fragile and hard to maintain
4. **Test generated Python code** with `python -c "$(cat /tmp/script.py)"` before deployment

## Related Documentation

- [Hook Development Patterns](../hooks/hook-development-patterns.md)
- [Pre-Commit Hook Implementation](../hooks/pre-commit-implementation.md)
