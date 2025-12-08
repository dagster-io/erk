# Documentation Extraction Plan: Kit CLI Push-Down Implementation Patterns

## Objective

Extract documentation from kit CLI push-down implementation sessions to improve future workflow automation work.

## Source Information

- **Plan Issue Session**: c3ff6452-0d88-4736-9c5a-d24df494e0bd (planning session for kit CLI push-down)
- **Implementation Sessions**: 670f0090-b586-4079-bb1c-48e1aca90a2f, f282ccbf-70a8-4ed9-b5b0-26c4f6644a28, 4e2e21e1-2515-4c0b-80fe-3557ff28ffb6

## Documentation Items

### Item 1: Kit CLI Testing Patterns for Workflow Integration

**Type**: Category B (Teaching Gap - documentation for what was BUILT)
**Location**: `docs/agent/kits/testing-kit-cli-commands.md`
**Action**: Create new document
**Priority**: High

**Rationale**: The implementation session created 32 unit tests for kit CLI commands using FakeGit and FakeGitHub. These patterns for testing workflow-integrated commands (JSON output validation, structured response testing) should be documented for future kit CLI development.

---

### Item 2: GitHub Actions Workflow Integration Patterns

**Type**: Category A (Learning Gap - would have made session faster)
**Location**: `docs/agent/kits/workflow-integration.md`
**Action**: Create new document
**Priority**: Medium

**Rationale**: The sessions spent time figuring out patterns for calling kit CLI commands from GitHub Actions workflows with proper JSON parsing and error handling. Documenting these patterns would accelerate future workflow automation.

---

### Item 3: Update docs/agent/index.md with new documents

**Type**: Category B (Routing update)
**Location**: `docs/agent/index.md`
**Action**: Update existing document
**Priority**: High (required for discoverability)

---

### Item 4: Glossary Entry for ISO 8601 Timestamps

**Type**: Category B (Teaching Gap)
**Location**: `docs/agent/glossary.md`
**Action**: Add glossary entry
**Priority**: Low

---

## Implementation Notes

- Items 1 and 2 are new documents that should be created in docs/agent/kits/
- Item 3 requires updating the auto-generated index (edit frontmatter, run dot-agent docs sync)
- Item 4 is a simple glossary addition

## Related Documentation to Load

- fake-driven-testing skill - For testing patterns context
- docs/agent/kits/push-down-pattern.md - Existing related documentation
