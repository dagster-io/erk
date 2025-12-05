---
title: GitHub Issue Limits
read_when:
  - Designing storage for large plans
  - Hitting "body is too long" API errors
  - Evaluating issue-based storage vs alternatives
---

# GitHub Issue Limits

Reference for GitHub platform limits relevant to erk plan storage.

## Comment Limits

| Limit                     | Value               | Notes                     |
| ------------------------- | ------------------- | ------------------------- |
| Characters per comment    | 65,536              | 4-byte unicode characters |
| Characters per issue body | 65,536              | Same as comments          |
| Comments per issue        | No documented limit | API paginates at 100/page |

## Storage Implications for Erk

- **Plan body + header:** Stored in issue body (65KB max)
- **Implementation plan:** Stored in first comment (65KB max)
- **Total per issue:** ~130KB guaranteed (body + 1 comment)
- **Overflow strategy:** Use multiple comments if plan exceeds 65KB

## Sources

- [GitHub Community Discussion #27190](https://github.com/orgs/community/discussions/27190)
- [GitHub Community Discussion #41331](https://github.com/orgs/community/discussions/41331)
