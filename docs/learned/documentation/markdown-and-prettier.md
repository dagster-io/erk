---
title: Markdown and Prettier
read_when:
  - writing or editing markdown documentation
  - understanding prettier's markdown formatting rules
  - resolving prettier violations in documentation
---

# Markdown and Prettier

Prettier formats markdown files in `docs/learned/` according to opinionated rules. Understanding these rules prevents formatting violations and ensures consistent documentation style.

## Prettier's Markdown Rules

### Line Length: 80 Characters (Soft Limit)

Prettier wraps prose at approximately 80 characters:

```markdown
This is a very long line that exceeds 80 characters and will be wrapped by prettier into multiple lines automatically.
```

Becomes:

```markdown
This is a very long line that exceeds 80 characters and will be wrapped by
prettier into multiple lines automatically.
```

**Exceptions:**

- URLs are never wrapped
- Code blocks are never wrapped
- Tables are not wrapped (but cells may wrap internally)

### List Formatting

**Bullet lists:**

```markdown
- First item
- Second item
  - Nested item
  - Another nested item
- Third item
```

**Numbered lists:**

```markdown
1. First item
2. Second item
3. Third item
```

Prettier normalizes list indentation and spacing.

### Table Formatting

Prettier aligns table columns:

**Before:**

```markdown
| Column 1 | Column 2               | Column 3 |
| -------- | ---------------------- | -------- |
| Short    | Very long content here | X        |
```

**After:**

```markdown
| Column 1 | Column 2               | Column 3 |
| -------- | ---------------------- | -------- |
| Short    | Very long content here | X        |
```

### Code Block Formatting

Prettier preserves code block content but normalizes fences:

````markdown
```python
def example():
    return "unchanged"
```
````

````

**Fence normalization:**

- Always uses triple backticks (not indentation)
- Language identifier is preserved
- Content indentation is unchanged

### Heading Spacing

Prettier enforces spacing around headings:

```markdown
## Heading

Content starts here.

## Another Heading

More content.
````

**Rules:**

- One blank line before headings
- One blank line after headings
- No blank line before first heading after frontmatter

### YAML Frontmatter

Prettier does NOT format YAML frontmatter:

```yaml
---
title: Example
read_when:
  - "condition 1"
  - "condition 2"
---
```

The frontmatter remains unchanged (indentation, quotes, spacing preserved).

## Common Prettier Violations

### Over-Length Lines

**Problem:** Prose lines exceed ~80 characters

**Fix:** Let prettier wrap automatically, or break manually at logical points

### Unaligned Tables

**Problem:** Table columns are misaligned

**Fix:** Run `prettier --write <file>` to auto-align

### Missing Blank Lines

**Problem:** No blank line before/after heading

**Fix:** Add blank lines around headings

## Running Prettier

### Format Single File

```bash
prettier --write docs/learned/path/to/file.md
```

### Format All Markdown

```bash
prettier --write "docs/learned/**/*.md"
```

### Check Without Formatting

```bash
prettier --check "docs/learned/**/*.md"
```

### CI Validation

The `make fast-ci` command includes prettier checks:

```bash
make fast-ci
```

This fails if any markdown files have formatting violations.

## Editor Integration

### VS Code

Install the Prettier extension:

```
ext install esbenp.prettier-vscode
```

Enable format on save in `.vscode/settings.json`:

```json
{
  "editor.formatOnSave": true,
  "[markdown]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

### Other Editors

See https://prettier.io/docs/en/editors.html for editor-specific setup.

## Prettier Configuration

Erk uses default prettier settings (no custom `.prettierrc`):

- Print width: 80
- Tab width: 2
- Prose wrap: always

## When to Ignore Prettier

Use `<!-- prettier-ignore -->` for special formatting:

```markdown
<!-- prettier-ignore -->
| Compact | Table | Here |
|---------|-------|------|
| A       | B     | C    |
```

**Use sparingly**: Only when default formatting breaks semantics.

## Related Documentation

- [stale-code-blocks-are-silent-bugs.md](stale-code-blocks-are-silent-bugs.md) — Why source pointers are better than code blocks
