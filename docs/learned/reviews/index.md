---
title: Code Review Agents
read_when:
  - "creating a new code review agent"
  - "understanding how automated code reviews work"
  - "modifying review agent behavior"
---

# Code Review Agents

Documentation for automated code review agents that run in CI.

## Overview

Review agents are markdown files in `.github/reviews/` with YAML frontmatter that define:

- File patterns to match
- Agent prompts
- Tool scoping
- Execution configuration

See [Convention-Based Reviews](../ci/convention-based-reviews.md) for the discovery and execution system.

## Review Agents

- [Test Coverage Agent](test-coverage-agent.md) - Categorizes files by testability and flags untested production code

## Adding New Agents

When creating a new review agent, document it here with:

- Purpose and scope
- File categorization logic (if applicable)
- Flagging criteria
- Output format
- Related tripwires

See [Test Coverage Agent](test-coverage-agent.md) as a reference implementation.
