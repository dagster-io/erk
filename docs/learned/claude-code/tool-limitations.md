---
title: Claude Code Tool Limitations
read_when:
  - "reading large files"
  - "file content appears truncated"
  - "plan appears incomplete after Read tool"
tripwires:
  - action: "reading a file over 2000 lines with the Read tool"
    warning: "Read tool truncates at 2000 lines by default. Use offset/limit parameters to page through large files, or use GitHub API for plan content."
---

# Claude Code Tool Limitations

## Read Tool Truncation

The Read tool has a default limit of 2000 lines. Files exceeding this are silently truncated.

**Impact:** Plan files fetched from GitHub and saved locally may appear incomplete if they exceed 2000 lines.

**Mitigation:**

- Use `offset` and `limit` parameters to page through large files
- For plan content, use `gh api` to fetch full content directly
- Check file line count with `wc -l` before reading if size is uncertain
