---
title: Workflow Capability Pattern
read_when:
  - creating GitHub workflow capabilities
  - adding CI review workflows
---

# Workflow Capability Pattern

Pattern for capabilities that install GitHub Actions workflows with prompts.

## Structure

A workflow capability typically installs:

1. `.github/workflows/<name>.yml` - The workflow file
2. `.github/prompts/<name>.md` - The prompt file
3. Optional: shared actions (e.g., `setup-claude-code`)

## Reference Implementation

`DignifiedReviewCapability` in `src/erk/core/capabilities/dignified_review.py` demonstrates the pattern.

**Key implementation points:**

1. **Artifacts property** - List both workflow and prompt files
2. **is_installed()** - Check if the workflow file exists
3. **preflight()** - Verify dependencies (e.g., required skill installed)
4. **install()** - Copy workflow and prompt from bundled source

The `get_bundled_github_dir()` function from `src/erk/artifacts/sync.py` provides the path to bundled `.github/` artifacts.

## Dependencies Pattern

If the workflow depends on shared actions (like `setup-claude-code`):

### Option 1: Require Dependency (Preflight Check)

Check for dependency in `preflight()` and fail with helpful message if missing. This is the preferred pattern when the dependency is installed by another capability.

### Option 2: Auto-Install Dependency (Self-Contained)

Install the action if missing during `install()`. Use this when the workflow should be fully self-contained.

## Checklist for New Workflow Capabilities

1. Create capability class in `src/erk/core/capabilities/`
2. Ensure workflow file exists in `.github/workflows/`
3. Ensure prompt file exists in `.github/prompts/`
4. Register in `registry.py` `_all_capabilities()` tuple
5. Add tests for `is_installed()` and `install()`
6. Document any dependencies in class docstring

## Related Topics

- [Capability System Architecture](capability-system.md) - Core capability system design
- [Bundled Artifacts System](bundled-artifacts.md) - How artifacts are bundled and synced
