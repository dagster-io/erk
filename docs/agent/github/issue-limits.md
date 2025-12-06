---
title: GitHub Issue Storage Limits
read_when:
  - "posting large content to GitHub issues"
  - "encountering comment size limits"
  - "designing GitHub issue storage strategy"
---

# GitHub Issue Storage Limits

## Comment Size Limit

**Maximum:** 65,536 characters per comment

**Implications:**

- Truncate content to ~65,000 chars (leave buffer)
- Add truncation notice if content exceeds limit
- Consider multi-comment chunking for large content

## Comment Count Limit

**Maximum:** No documented limit

**Observed:**

- GitHub supports thousands of comments per issue
- API paginates at 30-100 comments per page
- Performance may degrade on very long threads

## Workarounds for Large Content

1. **Multi-comment chunking:** Post n comments with "Part 1/3" headers
2. **External storage:** Link to gists or raw files
3. **Compression:** Use session preprocessing to reduce size

## Code Example

```python
MAX_COMMENT_SIZE = 65_000  # Leave buffer

if len(content) > MAX_COMMENT_SIZE:
    truncated = content[:MAX_COMMENT_SIZE]
    truncated += "\n\n[TRUNCATED - original size: {} chars]".format(len(content))
    content = truncated
```

## Related

- Metadata Block Rendering: [docs/agent/github/markdown-escaping.md](markdown-escaping.md)
- Multi-Comment Chunking: Plan #2332
