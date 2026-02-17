"""LearnedDocsCapability - agent-discoverable documentation system."""

import shutil
from pathlib import Path

from erk.artifacts.paths import get_bundled_claude_dir, get_bundled_codex_dir
from erk.core.capabilities.base import (
    Capability,
    CapabilityArtifact,
    CapabilityResult,
    CapabilityScope,
    ManagedArtifact,
    backend_agent_dir,
)
from erk_shared.context.types import AgentBackend

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
        return (
            "docs/learned/, .claude/skills/learned-docs/,"
            " and .claude/agents/learn/ directories exist"
        )

    @property
    def artifacts(self) -> list[CapabilityArtifact]:
        # Note: Category tripwires (e.g., architecture/tripwires.md) are auto-generated
        # by 'erk docs sync' from document frontmatter, not listed here as static artifacts
        return [
            CapabilityArtifact(path="docs/learned/", artifact_type="directory"),
            CapabilityArtifact(path="docs/learned/README.md", artifact_type="file"),
            CapabilityArtifact(path="docs/learned/index.md", artifact_type="file"),
            CapabilityArtifact(path=".claude/skills/learned-docs/", artifact_type="directory"),
            CapabilityArtifact(path=".claude/skills/learned-docs/SKILL.md", artifact_type="file"),
            CapabilityArtifact(path=".claude/agents/learn/", artifact_type="directory"),
            CapabilityArtifact(path=".claude/commands/erk/learn.md", artifact_type="file"),
        ]

    @property
    def managed_artifacts(self) -> list[ManagedArtifact]:
        """Declare learned-docs skill, learn command, and learn agent as managed artifacts."""
        return [
            ManagedArtifact(name="learned-docs", artifact_type="skill"),
            ManagedArtifact(name="learn", artifact_type="command"),
            ManagedArtifact(name="learn", artifact_type="agent"),
        ]

    def is_installed(self, repo_root: Path | None, *, backend: AgentBackend) -> bool:
        """Check if all three learned-docs directories exist."""
        assert repo_root is not None, "LearnedDocsCapability requires repo_root"
        agent_dir = backend_agent_dir(backend)
        return (
            (repo_root / "docs" / "learned").exists()
            and (repo_root / agent_dir / "skills" / "learned-docs").exists()
            and (repo_root / agent_dir / "agents" / "learn").exists()
        )

    def install(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        """Create docs/learned/ directory, learned-docs skill, learn command, and learn agent."""
        assert repo_root is not None, "LearnedDocsCapability requires repo_root"
        created_files: list[str] = []

        agent_dir = backend_agent_dir(backend)
        if backend == "codex":
            bundled_dir = get_bundled_codex_dir()
        else:
            bundled_dir = get_bundled_claude_dir()

        # Create docs/learned/ directory
        docs_dir = repo_root / "docs" / "learned"
        if not docs_dir.exists():
            docs_dir.mkdir(parents=True)
            created_files.append("docs/learned/")

            (docs_dir / "README.md").write_text(LEARNED_DOCS_README, encoding="utf-8")
            created_files.append("docs/learned/README.md")

            (docs_dir / "index.md").write_text(LEARNED_DOCS_INDEX, encoding="utf-8")
            created_files.append("docs/learned/index.md")
            # Note: Category tripwires (e.g., architecture/tripwires.md) are auto-generated
            # by 'erk docs sync' from document frontmatter

        # Create skill
        skill_dir = repo_root / agent_dir / "skills" / "learned-docs"
        if not skill_dir.exists():
            skill_dir.mkdir(parents=True)
            created_files.append(f"{agent_dir}/skills/learned-docs/")

        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            skill_file.write_text(LEARNED_DOCS_SKILL, encoding="utf-8")
            created_files.append(f"{agent_dir}/skills/learned-docs/SKILL.md")

        # Copy learn agent directory from bundled artifacts
        learn_agent_src = bundled_dir / "agents" / "learn"
        learn_agent_dst = repo_root / agent_dir / "agents" / "learn"

        if learn_agent_src.exists() and not learn_agent_dst.exists():
            learn_agent_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(learn_agent_src, learn_agent_dst)
            created_files.append(f"{agent_dir}/agents/learn/")

        # Copy learn command from bundled artifacts
        learn_cmd_src = bundled_dir / "commands" / "erk" / "learn.md"
        learn_cmd_dst = repo_root / agent_dir / "commands" / "erk" / "learn.md"

        if learn_cmd_src.exists() and not learn_cmd_dst.exists():
            learn_cmd_dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(learn_cmd_src, learn_cmd_dst)
            created_files.append(f"{agent_dir}/commands/erk/learn.md")

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

    def uninstall(self, repo_root: Path | None, *, backend: AgentBackend) -> CapabilityResult:
        """Remove docs/learned/ directory, learned-docs skill, learn command, and learn agent."""
        assert repo_root is not None, "LearnedDocsCapability requires repo_root"

        removed: list[str] = []
        agent_dir = backend_agent_dir(backend)

        # Remove skill directory
        skill_dir = repo_root / agent_dir / "skills" / "learned-docs"
        if skill_dir.exists():
            shutil.rmtree(skill_dir)
            removed.append(f"{agent_dir}/skills/learned-docs/")

        # Remove learn agent directory
        learn_agent_dir = repo_root / agent_dir / "agents" / "learn"
        if learn_agent_dir.exists():
            shutil.rmtree(learn_agent_dir)
            removed.append(f"{agent_dir}/agents/learn/")

        # Remove learn command file
        learn_cmd_file = repo_root / agent_dir / "commands" / "erk" / "learn.md"
        if learn_cmd_file.exists():
            learn_cmd_file.unlink()
            removed.append(f"{agent_dir}/commands/erk/learn.md")

        # Preserve docs/learned/ - it contains user-created documentation

        if not removed:
            return CapabilityResult(
                success=True,
                message="learned-docs not installed",
            )

        return CapabilityResult(
            success=True,
            message=f"Removed {', '.join(removed)} (docs/learned/ preserved)",
        )
