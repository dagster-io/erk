---
title: Cross-Repo Plans
read_when:
  - "setting up plans in a separate repository"
  - "configuring [plans] repo in config.toml"
  - "understanding cross-repo issue closing syntax"
---

# Cross-Repo Plans

Store plan issues in a dedicated repository while implementing in another.

## When to Use

- **Private plans**: Keep plan issues in a private repo while implementing in a public repo
- **Centralized planning**: Consolidate all plans across multiple implementation repos
- **Separation of concerns**: Keep implementation repos focused on code, not planning issues

## Configuration

Add to `{erks_dir}/config.toml`:

```toml
[plans]
repo = "owner/plans-repo"
```

Where `owner/plans-repo` is the GitHub repository that will hold plan issues.

## Behavior

### Issue Creation

When `[plans] repo` is configured:

- `gh issue create` commands use `-R owner/plans-repo` flag
- Issues are created in the plans repo, not the current repo

### Plan Header Metadata

The `source_repo` field in plan-header tracks where implementation happens:

```yaml
schema_version: "2"
created_at: 2025-01-15T10:30:00Z
created_by: username
source_repo: owner/impl-repo # Implementation happens here
```

This enables the plans repo to track which repo will implement each plan.

### PR Closing Syntax

PRs in the implementation repo use cross-repo syntax to close issues:

```
Closes owner/plans-repo#123
```

GitHub automatically closes the issue in the plans repo when the PR merges.

### Plan Listing

`erk plan list` shows an `impl-repo` column when cross-repo plans exist:

```
#    Title                      impl-repo      Status
123  Add authentication         owner/api      In Progress
124  Update docs                owner/docs     Open
```

## Related Documentation

- [Plan Schema Reference](plan-schema.md) - Complete plan-header field reference
- [Glossary: Repo Config](../glossary.md#repo-config) - Configuration file structure
