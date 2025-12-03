---
name: agent-docs
description: This skill should be used when writing, modifying, or reorganizing
  documentation in docs/agent/. Use when creating new documents, updating frontmatter,
  choosing categories, creating index files, updating routing tables, or moving
  files between categories. Essential for maintaining consistent documentation structure.
---

# Agent Documentation Guide

Overview: `docs/agent/` contains agent-focused documentation with:

- YAML frontmatter for routing and discovery
- Hierarchical category organization (10 categories)
- Index files for category navigation
- Routing tables in AGENTS.md

## Frontmatter Requirements

Every markdown file (except index.md) MUST have:

```yaml
---
title: Document Title
read_when:
  - "first condition"
  - "second condition"
---
```

### Required Fields

| Field       | Type         | Purpose                                    |
| ----------- | ------------ | ------------------------------------------ |
| `title`     | string       | Human-readable title for index tables      |
| `read_when` | list[string] | Conditions when agent should read this doc |

### Writing Effective read_when Values

- Use gerund phrases: "creating a plan", "styling CLI output"
- Be specific: "fixing merge conflicts in tests" not "tests"
- Include 2-4 conditions covering primary use cases
- Think: "An agent should read this when they are..."

Good:

```yaml
read_when:
  - "creating or closing plans"
  - "understanding plan states"
  - "working with .impl/ folders"
```

Bad:

```yaml
read_when:
  - "plans" # Too vague
  - "the user asks" # Not descriptive
```

## Documentation Structure

**Read the master index for current categories and documents:**

`docs/agent/index.md`

The index contains:

- All category paths and descriptions
- Root-level documents
- Document listings with "Read when..." conditions

## Category Placement Guidelines

1. **Match by topic** - Does the doc clearly fit one category?
2. **Match by related docs** - Are similar docs already in a category?
3. **When unclear** - Place at root level; categorize later when patterns emerge
4. **Create new category** - When 3+ related docs exist at root level

## Document Structure Template

```markdown
---
title: [Clear Document Title]
read_when:
  - "[first condition]"
  - "[second condition]"
---

# [Title Matching Frontmatter]

[1-2 sentence overview]

## [Main Content Sections]

[Organized content with clear headers]

## Related Topics

- [Link to related docs](../category/doc.md) - Brief description
```

## Index File Template

Each category has an `index.md` following this pattern:

```markdown
---
title: [Category] Documentation
read_when:
  - "[when to browse this category]"
---

# [Category] Documentation

[Brief category description]

## Quick Navigation

| When you need to... | Read this        |
| ------------------- | ---------------- |
| [specific task]     | [doc.md](doc.md) |

## Documents in This Category

### [Document Title]

**File:** [doc.md](doc.md)

[1-2 sentence description]

## Related Topics

- [Other Category](../other/) - Brief relevance
```

## Reorganizing Documentation

When moving files between categories:

### Step 1: Move Files with git mv

```bash
cd docs/agent
git mv old-location/doc.md new-category/doc.md
```

### Step 2: Update Cross-References

Find all references to moved files:

```bash
grep -r "old-filename.md" docs/agent/
```

Update relative links:

- Same category: `[doc.md](doc.md)`
- Different category: `[doc.md](../category/doc.md)`
- To category index: `[Category](../category/)`

### Step 3: Update Index Files

Update Quick Navigation tables in affected index files.

### Step 4: Update AGENTS.md

If the doc was in the routing table, update the path.

### Step 5: Validate

Run `make fast-ci` to catch broken links and formatting issues.

## Updating Routing Tables

AGENTS.md contains the Quick Routing Table for agent navigation.

### When to Add Entries

- New category additions
- High-frequency tasks
- Tasks where wrong approach is common

### Entry Format

```markdown
| [Task description] | → [Link or skill] |
```

Examples:

- `| Understand project architecture | → [Architecture](docs/agent/architecture/) |`
- `| Write Python code | → Load \`dignified-python\` skill FIRST |`

## Validation

Run before committing:

```bash
make fast-ci
```

This validates:

- YAML frontmatter syntax
- Required fields present
- Markdown formatting (prettier)

## Quick Reference

- Full navigation: [docs/agent/guide.md](docs/agent/guide.md)
- Category index: [docs/agent/index.md](docs/agent/index.md)
- Run validation: `make fast-ci`
