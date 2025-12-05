# GitHub Platform Limits Documentation

## Objective

Create a new `docs/agent/github/` folder with reference documentation for GitHub API and platform limits relevant to erk's issue-based plan storage.

## Source Information

- Session ID: b32694bd-c390-47ac-9949-0a87bac1af09
- Context: Research on GitHub issue comment limits for extraction plan storage

## Documentation Items

### 1. GitHub Issue Limits Reference

- **Type:** Category A (Learning Gap)
- **Location:** `docs/agent/github/issue-limits.md`
- **Action:** Create new file
- **Priority:** Medium (useful reference, not blocking)

#### Content

```markdown
# GitHub Issue Limits

Reference for GitHub platform limits relevant to erk plan storage.

## Comment Limits

| Limit | Value | Notes |
|-------|-------|-------|
| Characters per comment | 65,536 | 4-byte unicode characters |
| Characters per issue body | 65,536 | Same as comments |
| Comments per issue | No documented limit | API paginates at 100/page |

## Storage Implications for Erk

- **Plan body + header:** Stored in issue body (65KB max)
- **Implementation plan:** Stored in first comment (65KB max)
- **Total per issue:** ~130KB guaranteed (body + 1 comment)
- **Overflow strategy:** Use multiple comments if plan exceeds 65KB

## Sources

- [GitHub Community Discussion #27190](https://github.com/orgs/community/discussions/27190)
- [GitHub Community Discussion #41331](https://github.com/orgs/community/discussions/41331)

## Read When...

- Designing storage for large plans
- Hitting "body is too long" API errors
- Evaluating issue-based storage vs alternatives
```

### 2. Update docs/agent/index.md

- **Type:** Category B (Teaching Gap)
- **Location:** `docs/agent/index.md`
- **Action:** Update to add GitHub section
- **Priority:** Low (routing update)

#### Content

Add to index.md:
```markdown
### GitHub

- **[issue-limits.md](github/issue-limits.md)** — Read when designing storage for large plans or hitting API size errors
```