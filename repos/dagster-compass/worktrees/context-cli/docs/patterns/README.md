# Architectural Patterns

This directory documents cross-cutting architectural patterns used throughout the Compass codebase.

## What Are Cross-Cutting Patterns?

Cross-cutting patterns are design approaches that span multiple modules and layers of the application. Unlike feature-specific code, these patterns:

- Apply consistently across the entire codebase
- Affect how components interact with external concerns (time, I/O, configuration)
- Enable testing without introducing brittleness
- Maintain clean separation between business logic and infrastructure

## Available Patterns

### [Dependency Injection](./dependency-injection.md)

Core pattern for managing dependencies and enabling testability without mocking frameworks.

**Use when:**

- Components need configurable behavior
- Tests require deterministic control over external systems
- Code needs to work in multiple contexts (production, testing, simulation)

**Key benefits:**

- Explicit dependencies in constructors
- Production defaults prevent boilerplate
- Pure DI without magic or frameworks
- Type-safe and IDE-friendly

### [Time Abstraction](./time-abstraction.md)

Pattern for injecting time providers to enable deterministic testing of time-dependent code.

**Use when:**

- Code uses `datetime.now()`, `time.time()`, or `asyncio.sleep()`
- Testing periodic tasks or scheduled operations
- Testing timeout behavior or rate limiting
- Measuring elapsed time or durations

**Key benefits:**

- Eliminates `asyncio.sleep()` from tests (saves ~24-31 seconds per run)
- Deterministic time advancement
- No timing-based test flakiness
- Tests complete instantly

## When to Document a Pattern

Document a pattern when:

1. **It crosses module boundaries** - Used in 3+ unrelated modules
2. **It affects testing strategy** - Tests would be harder without it
3. **It has non-obvious benefits** - Developers might miss the value
4. **It requires coordination** - Multiple implementers need alignment
5. **It replaces a common antipattern** - Prevents mistakes

## Pattern Documentation Structure

Each pattern document should include:

1. **Problem Statement** - What issue does this solve?
2. **Solution Overview** - High-level approach
3. **Implementation Guide** - How to use it correctly
4. **Examples** - Production and test code samples
5. **Common Pitfalls** - What to avoid
6. **Related Patterns** - How it composes with others

## Adding New Patterns

Before adding a new pattern:

1. Verify it's truly cross-cutting (not feature-specific)
2. Check if it extends an existing pattern
3. Gather real examples from the codebase
4. Document both "do" and "don't" examples
5. Update this README with a link and description

## Pattern Evolution

Patterns evolve over time:

- **Established** - Proven across multiple modules, stable API
- **Emerging** - In use but API may change
- **Deprecated** - Being replaced by better approach

Mark pattern status clearly in the document header.

## References

- [CLAUDE.md](../../CLAUDE.md) - Project-wide standards including "dignified Python" principles
- [csbot/utils/](../../packages/csbot/src/csbot/utils/) - Utility modules implementing common patterns
