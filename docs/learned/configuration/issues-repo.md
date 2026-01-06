---
title: External Issues Repository Configuration
read_when:
  - "configuring plans to be stored in a separate repository"
  - "setting up plans.repo in config.toml"
---

# External Issues Repository Configuration

Configure erk to store plan issues in a separate repository from your working repository.

## Configuration

In `.erk/config.toml`:

```toml
[plans]
repo = "owner/repo"
```

**Format:** `"owner/repo"` - the GitHub repository where plan issues will be created.

**Example:**

```toml
[plans]
repo = "myorg/engineering-plans"
```

## Effect

When `plans.repo` is set:

- Plan issues are created in the target repository instead of the working repository
- `erk implement` fetches plans from the target repository
- `erk doctor` checks that required labels exist in the target repository

## Required Labels

Erk uses these labels to organize plan issues:

| Label            | Color              | Description                              |
| ---------------- | ------------------ | ---------------------------------------- |
| `erk-plan`       | `#0E8A16` (green)  | Implementation plan for manual execution |
| `erk-objective`  | `#5319E7` (purple) | Multi-phase objective with roadmap       |
| `erk-extraction` | `#D93F0B` (orange) | Documentation extraction plan            |

### Automatic Label Setup

When you run `erk init` with `plans.repo` configured, erk will offer to create these labels in the target repository. You need write access to the target repository.

### Manual Label Setup

If automatic setup fails, create labels manually in GitHub:

1. Go to your target repository's Issues tab
2. Click "Labels" in the sidebar
3. Create each label with the name, color, and description from the table above

## Use Cases

**Centralized planning:** Store all plan issues in a dedicated repository while implementing in multiple code repositories.

**Team visibility:** Keep plan issues visible to the team without cluttering the code repository's issue tracker.

**Access separation:** Allow broader access to plan issues while restricting code repository access.

## Verification

Run `erk doctor` to verify the setup:

```bash
erk doctor
```

Look for the "plans-repo-labels" check. If labels are missing, the check will fail with instructions to fix.
