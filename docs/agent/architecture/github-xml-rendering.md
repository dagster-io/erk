---
title: GitHub Markdown XML Rendering
read_when:
  - "embedding XML content in GitHub issues or PRs"
  - "creating metadata blocks with angle-bracket syntax"
  - "XML tags disappearing in rendered GitHub markdown"
---

# GitHub Markdown XML Rendering

## Problem

When embedding XML content in GitHub issue comments or PR bodies, tags like `<session>`, `<user>`, `<assistant>` are interpreted as HTML and disappear from the rendered output.

**Example of the problem:**

```markdown
Session data:
<session>
<user>Content here</user>
</session>
```

When rendered on GitHub, the `<session>` and `<user>` tags vanish because GitHub treats them as HTML tags.

## Solution

Always wrap XML content in code fences with the `xml` language identifier:

````markdown
```xml
<session>
  <user>Content here</user>
</session>
```
````

## When This Applies

- **Embedding preprocessed session XML** in extraction plan issues
- **Any metadata block containing XML-like content**
- **Debug output that includes angle-bracket syntax**
- **Issue/PR bodies with structured data**

## Key Insight

Some content is double-escaped (e.g., `&lt;command-message&gt;`) while structural tags are not. The code fence approach handles both correctly:

- Structural tags like `<session>`, `<user>` are preserved
- Already-escaped entities like `&lt;command-message&gt;` remain escaped
- Syntax highlighting improves readability

## Related Patterns

- See [metadata-blocks.md](metadata-blocks.md) for session-content metadata block format
- See [github-parsing.md](github-parsing.md) for GitHub URL parsing patterns

## Example: Session Content Metadata Block

````markdown
<!-- erk:metadata-block:session-content -->
<details>
<summary><strong>Session Data (1/3): fix-auth-bug</strong></summary>

```xml
<session>
  <user>Can you fix the authentication bug?</user>
  <assistant>Let me investigate the auth flow...</assistant>
</session>
```

</details>
````

This pattern ensures XML content renders correctly in GitHub while maintaining machine-parseable structure.
