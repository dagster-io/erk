"""LearnedDocsCapability - agent-discoverable documentation system."""

from pathlib import Path

from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
)

LEARNED_DOCS_README = """\
---
title: "Learned Documentation Guide"
read_when:
  - "setting up learned docs"
  - "understanding learned docs structure"
  - "adding new documentation"
---

# Learned Documentation

This directory contains agent-discoverable documentation for AI assistants.

## Purpose

Learned docs provide structured guidance that AI agents can discover based on \
`read_when` conditions in frontmatter.

## Structure

Each markdown file requires YAML frontmatter:

- `title`: Document title (required)
- `read_when`: Conditions for when to read (required)
- `tripwires` (optional): Action-triggered rules

## Commands

- `erk docs sync` - Regenerate index files from frontmatter
- `erk docs validate` - Validate frontmatter

## Getting Started

1. Create markdown files with proper frontmatter
2. Organize related docs in subdirectories (categories)
3. Run `erk docs sync` to generate index files
"""

LEARNED_DOCS_INDEX = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk docs sync' to regenerate this file from document frontmatter. -->

# Agent Documentation

This index provides top-down navigation for agent-discoverable documentation.
Use the `read_when` conditions listed with each document to decide what to read
based on your current task. This enables progressive disclosure - read only what
you need, when you need it.

<!-- This index is automatically populated by 'erk docs sync'. -->

## Categories

<!-- Subdirectories will be listed here once created. -->

## Uncategorized

<!-- Top-level documents will be listed here. -->
<!-- Example: **[my-doc.md](my-doc.md)** — when to read condition 1, condition 2 -->
"""

LEARNED_DOCS_TRIPWIRES = """\
<!-- AUTO-GENERATED FILE - DO NOT EDIT DIRECTLY -->
<!-- Run 'erk docs sync' to regenerate this file from document frontmatter. -->

# Tripwires

Action-triggered rules that fire when you're about to perform specific actions.

Tripwires serve as a last line of defense against rule violations. Agents balance
competing objectives and can inadvertently violate codebase rules despite their
best efforts. Tripwires catch these cases by triggering when an agent is about
to take a specific action, prompting them to read the full document before
proceeding. Code review agents can also use tripwires to detect violations and
examine the referenced documentation to determine if an issue is real.

<!-- Tripwires are collected from the 'tripwires' frontmatter field in documents. -->
<!-- Each tripwire should follow this format in your document's frontmatter: -->
<!--
---
title: "My Document"
read_when:
  - "working on feature X"
tripwires:
  - trigger: "Before doing action Y"
    action: "Read this document first. Explains why Y needs special handling."
---
-->

<!-- Currently empty. Add tripwires to your documents and run 'erk docs sync'. -->
"""

LEARNED_DOCS_SKILL = """\
---
name: learned-docs
description: This skill should be used when writing, modifying, or reorganizing
  documentation in docs/learned/. Use when creating new documents, updating frontmatter,
  choosing categories, creating index files, updating routing tables, or moving
  files between categories. Essential for maintaining consistent documentation structure.
---

# Learned Documentation Guide

Overview: `docs/learned/` contains agent-focused documentation with:

- YAML frontmatter for routing and discovery
- Hierarchical category organization
- Index files for category navigation

## Document Registry

@docs/learned/index.md

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
```

## Category Placement Guidelines

1. **Match by topic** - Does the doc clearly fit one category?
2. **Match by related docs** - Are similar docs already in a category?
3. **When unclear** - Place at root level; categorize later when patterns emerge
4. **Create new category** - When 3+ related docs exist at root level

## Validation

Run before committing:

```bash
erk docs sync      # Regenerate index files
erk docs validate  # Check frontmatter
```

## Quick Reference

- Category index: docs/learned/index.md
- Regenerate indexes: `erk docs sync`
"""


class LearnedDocsCapability(Capability):
    """Capability for the learned-docs agent documentation system."""

    @property
    def name(self) -> str:
        return "learned-docs"

    @property
    def description(self) -> str:
        return "Autolearning documentation system"

    @property
    def scope(self) -> CapabilityScope:
        return "project"

    @property
    def installation_check_description(self) -> str:
        return "docs/learned/ directory exists"

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        return [
            CapabilityArtifact(path="docs/learned/", artifact_type="directory"),
            CapabilityArtifact(path="docs/learned/README.md", artifact_type="file"),
            CapabilityArtifact(path="docs/learned/index.md", artifact_type="file"),
            CapabilityArtifact(path="docs/learned/tripwires.md", artifact_type="file"),
            CapabilityArtifact(path=".claude/skills/learned-docs/", artifact_type="directory"),
            CapabilityArtifact(path=".claude/skills/learned-docs/SKILL.md", artifact_type="file"),
        ]

    def is_installed(self, repo_root: Path | None) -> bool:
        """Check if docs/learned/ directory exists."""
        assert repo_root is not None, "LearnedDocsCapability requires repo_root"
        return (repo_root / "docs" / "learned").exists()

    def install(self, repo_root: Path | None) -> CapabilityResult:
        """Create docs/learned/ directory and learned-docs skill."""
        assert repo_root is not None, "LearnedDocsCapability requires repo_root"
        created_files: list[str] = []

        # Create docs/learned/ directory
        docs_dir = repo_root / "docs" / "learned"
        if not docs_dir.exists():
            docs_dir.mkdir(parents=True)
            created_files.append("docs/learned/")

            (docs_dir / "README.md").write_text(LEARNED_DOCS_README, encoding="utf-8")
            created_files.append("docs/learned/README.md")

            (docs_dir / "index.md").write_text(LEARNED_DOCS_INDEX, encoding="utf-8")
            created_files.append("docs/learned/index.md")

            (docs_dir / "tripwires.md").write_text(LEARNED_DOCS_TRIPWIRES, encoding="utf-8")
            created_files.append("docs/learned/tripwires.md")

        # Create skill
        skill_dir = repo_root / ".claude" / "skills" / "learned-docs"
        if not skill_dir.exists():
            skill_dir.mkdir(parents=True)
            created_files.append(".claude/skills/learned-docs/")

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            skill_file.write_text(LEARNED_DOCS_SKILL, encoding="utf-8")
            created_files.append(".claude/skills/learned-docs/SKILL.md")

        if not created_files:
            return CapabilityResult(
                success=True,
                message="docs/learned/ already exists",
            )

        return CapabilityResult(
            success=True,
            message="Created docs/learned/",
            created_files=tuple(created_files),
        )
