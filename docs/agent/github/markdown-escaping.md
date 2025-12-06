---
title: GitHub Markdown Escaping
read_when:
  - "posting session content to GitHub issues"
  - "seeing XML tags disappear in GitHub comments"
  - "working with metadata blocks in GitHub"
---

# GitHub Markdown Escaping

## Problem: XML/HTML Tags Disappear

GitHub interprets tags like `<session>`, `<user>`, `<assistant>` as HTML elements. If the tag isn't recognized HTML, it renders invisibly.

## Solution: Code Fences

Always wrap XML or code-like content in triple-backtick code fences with language tags:

````markdown
```xml
<session>
  <user>message</user>
  <assistant>response</assistant>
</session>
```
````

## When to Use

- Session XML preprocessed output
- Any content with angle brackets `< >`
- Code snippets with HTML/XML-like syntax
- Metadata blocks containing structured data

## Related

- GitHub Issue Limits: [docs/agent/github/issue-limits.md](issue-limits.md)
- Session Content Metadata Blocks: Plan #2332
