# Extraction Plan: Test Setup Patterns for CLI Validation

## Objective

Document the pattern for updating tests when adding validation to existing CLI commands.

## Source Information

- **Session ID**: c1a8d09e-9f52-4b73-9d4a-ef4a24a0e815
- **Context**: Implementation of docs/agent initialization feature

---

## Documentation Items

### Item 1: Test Setup Helper Pattern for Command Preconditions

**Type**: Category B (Teaching Gap - documenting what was built)

**Location**: `docs/agent/testing/` (new file or addition to existing)

**Action**: Create

**Priority**: Medium (useful pattern that will recur)

**Rationale**: When adding validation to CLI commands (like checking docs/agent exists before create-extraction-plan), all existing tests for that command break. The solution is a helper function that establishes required preconditions.

**Draft Content**:

```markdown
---
title: Test Setup Patterns for CLI Commands
read_when:
  - "adding validation to existing CLI commands"
  - "fixing broken tests after adding command preconditions"
---

# Test Setup Patterns for CLI Commands

## Problem

When you add validation to a CLI command (e.g., checking that a directory exists before proceeding), all existing tests for that command will fail because they don't set up the required state.

## Solution: Precondition Helper Functions

Create a helper function that establishes the minimum required state for the command to proceed past validation.

### Example: docs/agent Validation

When `create-extraction-plan` was updated to require `docs/agent/` to exist:

\`\`\`python
def _setup_docs_agent(tmp_path: Path) -> None:
    """Set up a minimal docs/agent directory for tests.

    The create-extraction-plan command validates that docs/agent exists and has
    at least one .md file before proceeding.
    """
    agent_docs = tmp_path / "docs" / "agent"
    agent_docs.mkdir(parents=True)
    # Create a minimal doc file to pass validation
    (agent_docs / "glossary.md").write_text(
        """---
title: Glossary
read_when:
  - "looking up terms"
---

# Glossary
""",
        encoding="utf-8",
    )
\`\`\`

### Usage Pattern

Add the helper call at the start of each test that invokes the command:

\`\`\`python
def test_create_extraction_plan_success(tmp_path: Path) -> None:
    _setup_docs_agent(tmp_path)  # Establish preconditions
    fake_gh = FakeGitHubIssues()
    runner = CliRunner()
    # ... rest of test
\`\`\`

## Key Principles

1. **Minimal setup**: Only create what's needed to pass validation
2. **Valid content**: If validation checks file format (like frontmatter), include valid content
3. **Scoped to tmp_path**: Use pytest's `tmp_path` fixture, never hardcoded paths
4. **Document purpose**: Docstring explains which command/validation this supports

## When to Use This Pattern

- Adding new validation to existing commands
- Fixing tests that fail after validation changes
- Creating tests for commands with preconditions
```