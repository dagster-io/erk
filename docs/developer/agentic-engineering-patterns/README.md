# Agentic Engineering Patterns

This section documents architectural patterns for building AI-powered development tools and workflows. These patterns capture design decisions, rationale, and best practices discovered through building the erk project.

## Purpose

This documentation serves two audiences:

1. **AI Assistants**: Conceptual understanding of WHAT patterns are and WHY they exist
2. **Human Developers**: Pattern catalog for design decisions and architectural guidance

## Relationship to Other Documentation

This section complements the existing `.erk/docs/agent/` folder:

| Section                                          | Purpose               | Focus                                                                   |
| ------------------------------------------------ | --------------------- | ----------------------------------------------------------------------- |
| **docs/developer/agentic-engineering-patterns/** | Pattern catalog       | WHAT patterns are (naming, concepts), WHY they exist (design rationale) |
| **.erk/docs/agent/**                             | Implementation guides | HOW to implement (step-by-step, technical details, code examples)       |

Both sections serve complementary roles in the documentation architecture.

## Documented Patterns

### 1. Agent-Delegating Commands

Commands that immediately delegate to specialized agents for workflow orchestration.

**Key Benefits:**

- Context reduction by declining accumulated command context
- Model selection flexibility (e.g., Haiku for fast execution)
- Clear separation of concerns (thin commands, thick agents)

**Documentation:** [agent-delegating-commands.md](agent-delegating-commands.md)

**Implementation Guide:** [../agent/command-agent-delegation.md](../agent/command-agent-delegation.md)

---

### 2. Kit CLI Preprocessing

Python commands for mechanical preprocessing before LLM inference.

**Key Benefits:**

- Testability: Full unit test coverage with pytest
- Reliability: Robust error handling, type safety
- Token efficiency: Reduces agent prompt size
- No permission prompts for deterministic operations

**Documentation:** [kit-cli-push-down.md](kit-cli-push-down.md)

**Implementation Guide:** [../agent/kit-cli-commands.md](../agent/kit-cli-commands.md)

---

## Contributing Patterns

When adding new patterns to this catalog:

1. Create a new markdown file in this directory
2. Update this README with a brief entry
3. Cross-link to relevant implementation guides in `.erk/docs/agent/`
4. Include examples from the actual codebase
5. Explain WHAT and WHY, not just HOW
