---
description: "Best practices for AI-assisted development"
---

# Agentic Programming Best Practices

Best practices for structuring code to be amenable to AI-assisted engineering.

---

## Introduction

This document presents best practices for **agentic programming** - the art of structuring code and development processes to maximize effectiveness when working with AI assistants.

### What is Agentic Programming?

Agentic programming is an emerging discipline focused on making codebases and workflows optimally compatible with AI-assisted development. It recognizes that AI agents have unique strengths and constraints that fundamentally differ from human developers.

Agents work within limited context windows that require efficient information architecture. Their stateless interactions need persistent documentation and planning files for continuity. Their pattern recognition capabilities benefit from consistent structures, and their parallel processing potential emerges when tasks are properly decomposed. Understanding these characteristics shapes how we structure code for agent collaboration.

### Document Philosophy

These practices are opinionated and prescriptive. They represent patterns that have proven effective across multiple projects and teams. Not every pattern will apply to every codebase, but understanding the principles will help you make informed decisions about your own AI-assisted development workflow.

Vibe alert: these guidelines have been developed from observed experience, rather than formal evaluations. We have not rigorously tested these techniques nor understand which ones are more effective than others relatively, and to the degree that they actually compound. These are formulated from intuition, first-principles reasoning, and from observed behavior during actual development.

---

## Glossary of Terms

Key terminology used throughout this document. For detailed explanations, see the linked sections.

**Agent Session** - A single, stateless interaction between a human and AI assistant working on code.

**Agentic Programming** - Structuring code and workflows to maximize effectiveness when working with AI assistants.

**Coarse-grained** - Working with larger, complete functional units rather than fine details. In modules: entire features in single files. In testing: whole subsystem interfaces rather than individual function mocks. See [Coarse-grained Modules](#coarse-grained-parallel-modules).

**Context Window** - The maximum amount of text an AI model can process in a single interaction, measured in tokens (roughly 3/4 of a word). Claude Code has per-file limits of ~25,000 tokens or ~6,000-8,000 lines of code before comprehension degrades. Exceeding these limits causes the AI to miss details, lose track of component relationships, or produce inconsistent outputs. Context window contents must remain consistent to maintain agent performance—violations known as context rot, context poisoning, and similar terms lead to degraded outputs. This makes modular architecture with smaller, coarse-grained modules essential for maintaining quality.

**Disposability** - Property of modules that can be deleted cleanly without unwinding dependencies. See [One Feature Per File](#key-pattern-one-feature-per-file).

**Fakes** - In-memory test implementations with injectable constructor state. See [Test Architecture](#test-architecture-coarse-grained-dependency-injection).

**Injectable State** - Test configuration passed via constructor parameters for explicit scenarios.

**Mental Model Document** - Distilled documentation of external tool behavior. See [External Tool Mental Models](#external-tool-mental-models).

**Parallel Modules** - Independent, self-contained code units enabling simultaneous development. See [Coarse-grained Parallel Modules](#coarse-grained-parallel-modules).

**Planning Documents** - Markdown files (.md) that capture implementation plans, preserving design decisions and execution blueprints across stateless agent sessions. See [Planning](#planning-iterative-design-before-implementation).

**Plan-based Development** - Creating detailed execution blueprints before implementation. See [Planning](#planning-iterative-design-before-implementation).

**Stateless Interactions** - Agents don't maintain memory between sessions, requiring planning documents and other persistent files for continuity.

**Token Cache** - Pre-materialized knowledge in `.agent` directory avoiding repeated discovery. See [Agent Documentation](#agent-documentation-the-agent-directory).

**Token Efficiency** - Optimizing information architecture to maximize useful content within context limits.

**Worktree** - Git feature enabling multiple working directories from one repository. See [Parallel Development](#parallel-development-with-worktrees-and-erk).

**Erk** - Orchestration tool providing simplified worktree lifecycle management, standardized conventions, and automatic plan document integration for parallel agentic development. See [Parallel Development](#parallel-development-with-worktrees-and-erk).

---

## Table of Contents

0. [Glossary of Terms](#glossary-of-terms) - Key terminology and definitions used throughout this document.

1. [Coarse-grained Parallel Modules](#coarse-grained-parallel-modules) - Organize code into independent, self-contained modules for efficient context management and safe disposability.

2. [Agent Documentation: The `.agent` Directory](#agent-documentation-the-agent-directory) - Create a token cache of persistent knowledge that agents can reference instead of rediscovering.

3. [External Tool Mental Models](#external-tool-mental-models) - Document how external tools and APIs work to prevent expensive rediscovery and incorrect assumptions.

4. [Planning: Iterative Design Before Implementation](#planning-iterative-design-before-implementation) - Invest in iterative planning with persistent documentation before implementation to reduce context thrashing and increase the complexity of tasks that can be performed autonomously.

5. [Advanced: Custom Tooling](#advanced-custom-tooling) - Custom development tools that amplify agentic programming capabilities:
   - [Dev-Only CLIs: Flat Script Architecture](#dev-only-clis-flat-script-architecture) - Build development CLIs as collections of self-contained PEP 723 scripts for maximum agent compatibility.
   - [Parallel Development with Worktrees and Erk](#parallel-development-with-worktrees-and-erk) - Enable parallel agentic sessions using Git worktrees and plan-based development workflows.

6. [Test Architecture: Coarse-Grained Dependency Injection](#test-architecture-coarse-grained-dependency-injection) - Structure tests using injectable dependencies with stateful fakes for efficient agent test authoring and fast feedback loops.

7. [Authoring Guidelines](#authoring-guidelines) - Guidelines for maintaining this document with professional tone and clear structure.

---

## Coarse-grained Parallel Modules

### Core Principle

Organize code into coarse-grained, parallel modules where each module handles a complete feature independently. When agents can see an entire feature in one file, they work faster and make fewer mistakes. When features fail, you can delete them cleanly without unwinding dependencies. This pattern transforms how agents interact with your codebase—from navigating mazes of interconnected files to working with discrete, understandable units.

### Key Pattern: One Feature Per File

**Structure Example:** CLI Commands

```
commands/
├── list.py      # Complete 'list' command - self-contained
├── create.py    # Complete 'create' command - independent
├── delete.py    # Complete 'delete' command - isolated
└── update.py    # Complete 'update' command - standalone
```

### Why This Pattern Works

The immediate benefit is context window efficiency. When each module contains a complete feature, agents can understand everything they need without loading multiple files or maintaining mental maps of cross-file dependencies. This isn't just convenient—it fundamentally changes what agents can accomplish.

For reference, Claude Code operates with a 25,000 token context window, which translates to approximately 6,000-8,000 lines of Python code depending on code density and complexity. Coarse-grained modules allow agents to load complete features within this limit.

Implementation becomes dramatically faster because agents can generate complete, working features in a single response. There's no coordination overhead, no careful sequencing of changes across files. You can even develop multiple features in parallel without conflicts, since each module stands alone.

Perhaps most importantly, failed experiments become cheap. Delete the file and the experiment is gone—no cleanup, no refactoring, no archaeological digs through the codebase to find orphaned code. This disposability encourages experimentation and rapid iteration.

**Note**: This pattern enables safe iteration, not careless coding. Each module should still follow your project's coding standards. Disposability refers to clean architectural boundaries, not to code quality.

### Self-Describing Features for Navigation

Include metadata and comments that make features self-describing and discoverable. This enables quick discovery without reading implementation details, automated documentation generation, and faster agent navigation to relevant code.

**Good Examples:**

```python
# CLI command with help text
@click.command("list")
@click.option("--format", help="Output format (json/table)")
def list_cmd():
    """List all available resources with filtering."""
    pass

# API endpoint with docstring
@app.route("/api/users")
def get_users():
    """GET /api/users - Retrieve paginated user list."""
    pass

# Plugin with manifest
class DataProcessor:
    """Process CSV files for reporting.

    Capabilities:
    - Input: CSV files up to 100MB
    - Output: JSON summary statistics
    - Performance: Suitable for batch processing
    """
```

### Example Applications

This pattern applies broadly to any system with parallel, independent features. CLI commands benefit from one command per file with complete implementation. API endpoints can each live in their own file with all related logic. Event handlers, report generators, data processors, and migration scripts all follow the same principle: features that can be added, modified, or removed independently without affecting sibling features.

The key characteristic is independence. If you can conceptually add or remove a feature without touching other features at the same level, it's a candidate for this pattern.

---

## Agent Documentation: The `.agent` Directory

### Core Principle

The `.agent` directory serves as a **token cache**—a persistent store of understanding that agents have already computed. Instead of repeatedly consuming thousands of tokens to understand the same patterns, conventions, and architectural decisions, agents can load pre-materialized knowledge. When an agent invests significant tokens to achieve deep understanding, persist that understanding for future reuse. This transforms expensive discovery into cheap retrieval.

### The Token Cache Concept

Think of the cache in terms of levels, similar to CPU caching. A CLAUDE.md file might serve as an L0 cache for the most critical, frequently-needed information. A QUICK_REFERENCE.md acts as an L1 cache for common lookups. Detailed guides like EXCEPTION_HANDLING.md form an L2 cache for deeper dives. Like any cache, these documents require invalidation and updates when the underlying reality changes.

### Structure Example

```
.agent/
├── ARCHITECTURE.md              # Architectural decisions
├── FEATURE_INDEX.md             # Feature documentation index
├── MODULE_MAP.md                # Module organization
├── packages/
│   └── agentic_programming_guide/
│       └── ...                  # Package-specific guides
└── tools/
    └── graphite.md              # External tool mental models

docs/
├── PATTERNS.md                  # Code patterns with examples
├── EXCEPTION_HANDLING.md        # Detailed exception philosophy
├── QUICK_REFERENCE.md           # Fast lookup tables
└── TESTING.md                   # Testing patterns and practices
```

### What Belongs in `.agent`

The `.agent` directory should contain knowledge that agents would otherwise need to derive repeatedly. Architectural decisions belong here—not just what patterns you use, but why you chose them over alternatives. Include pattern libraries showing correct implementations, especially for complex operations that span multiple files or systems.

Mental models earn their place when they help agents reason about non-obvious subsystems. If an agent needs to understand that your event system uses eventual consistency, or that your API versioning follows specific rules, document these models explicitly. Tool-specific guides prove valuable when external tools require particular workflows—how to structure commits for Graphite, or which deployment commands to run in what order.

Keep user-facing documentation in standard locations. The `.agent` directory isn't for getting started guides or API references—it's for the deep operational knowledge that makes agents effective. Marketing content, user tutorials, and general README files belong in their traditional locations, not hidden in an agent-specific directory.

### Key Characteristics

#### Agent-First Writing Style

Documentation optimized for AI consumption differs from human-oriented writing. Structure information for rapid scanning and extraction. Use imperative statements and clear hierarchies rather than conversational prose.

**Example:**

```markdown
## Exception Handling

🔴 **MUST**: Never use try/except for control flow
🟡 **SHOULD**: Check conditions with if statements
🟢 **MAY**: Catch at error boundaries for user messages

**Acceptable uses:**

- CLI error boundaries for user-friendly messages
- Third-party APIs that require exception handling
- Adding context before re-raising
```

This direct style helps agents quickly extract rules and apply them consistently.

#### Rich Examples Over Prose

Show patterns through contrasting examples rather than lengthy explanations. Agents excel at pattern matching, so give them patterns to match.

````markdown
## Path Operations

Correct approach:

```python
if path.exists():
    resolved = path.resolve()
```

Problematic approach:

```python
resolved = path.resolve()  # May fail if path doesn't exist
```
````

The contrast makes the pattern immediately clear without requiring paragraph-long explanations.

#### Rapid Navigation

Include tables and quick references for common decision points:

```markdown
| If you're writing... | Check this...                         |
| -------------------- | ------------------------------------- |
| Exception handling   | → Exception Handling section          |
| Subprocess calls     | → Always use check=True               |
| Path operations      | → Validate existence before resolving |
```

These navigation aids help agents quickly locate relevant guidance without loading entire documents.

### Integration with Main Codebase Documentation

CLAUDE.md in the root provides quick reference and critical rules, linking to `.agent` for comprehensive details. This two-tier approach gives agents both a fast path for common operations and a deep path for complex scenarios without loading unnecessary context.

For example, CLAUDE.md might contain: "Prefer checking conditions over using try/except for control flow. Full guide: [.agent/docs/EXCEPTION_HANDLING.md]" while the linked document provides comprehensive examples, edge cases, and rationale.

### Maintenance Guidelines

Update documentation when understanding deepens—when agents discover new patterns worth preserving or when existing patterns prove insufficient. Refactor when the same documentation gets consulted repeatedly, signaling its value. Delete outdated documentation ruthlessly, as stale guidance causes more harm than missing guidance. Keep the root CLAUDE.md synchronized with `.agent` details to maintain consistency.

### Known Risk: Documentation Drift

Documentation drift represents a critical challenge in agentic engineering. The `.agent` documentation can become outdated as the codebase evolves, leading agents to follow obsolete patterns or incorrect assumptions. Stale agent documentation actively harms development by wasting tokens and introducing bugs.

This remains an unsolved problem. We lack robust tooling to detect when `.agent` files diverge from actual code patterns. Current mitigation relies on manual review and agent prompting to verify documentation accuracy. The solution space requires proper tooling—automated drift detection, tests that validate documentation claims against code, and integration into CI/CD pipelines. Until then, treat `.agent` maintenance as a manual, high-priority task.

### The Compound Effect

The `.agent` directory creates compound value over time. Each agent session that would have spent thousands of tokens deriving understanding instead loads it directly. This isn't just faster—it's more consistent and accurate, since all agents reference the same canonical patterns rather than developing their own interpretations. As agents contribute new discoveries back to this shared knowledge base, the entire system becomes more capable.

### Anti-Pattern: Human-Centric Documentation in `.agent`

Avoid placing tutorial-style, beginner-focused content in `.agent`:

```markdown
# Getting Started with Our Codebase

Welcome! We're excited to have you here. Let's walk through how to set up
your development environment step by step...
```

This content belongs in root README.md or docs/CONTRIBUTING.md for humans. The `.agent` directory should contain machine-optimized references. Humans rarely look there, agents don't need tutorials, and mixing audiences dilutes both experiences.

---

## External Tool Mental Models

### Core Principle

Many projects depend on external tools that agents need to understand deeply—specialized build systems, deployment pipelines, API clients, or domain-specific utilities. These tools often emerged after an agent's training cutoff or exist in niche domains where documentation is scattered. Creating comprehensive mental model documents for these tools transforms expensive discovery into efficient loading of pre-computed understanding. These documents are natural candidates for the `.agent` directory, where they serve as reusable knowledge artifacts.

### Naming Convention

To enable scalability and discoverability, mental model documents follow a consistent naming pattern within the `.agent/tools/` subdirectory:

```
.agent/tools/<tool_name>.md
```

Examples:

- `.agent/tools/graphite.md` - Graphite CLI mental model
- `.agent/tools/terraform.md` - Terraform infrastructure tool
- `.agent/tools/bazel.md` - Bazel build system
- `.agent/tools/kubernetes.md` - Kubernetes orchestration

This convention organizes tool documentation in a dedicated subdirectory, making it immediately recognizable and creating a predictable namespace for external tool knowledge.

### Why This Matters

When agents encounter unfamiliar tools, they resort to web searches, parsing HTML documentation into usable knowledge. This process repeats for every agent session, creating inefficiency and inconsistency. Worse, agents may make incorrect assumptions based on superficial similarity to other tools they know.

Documenting tool mental models once creates reusable knowledge that every agent can leverage immediately. This investment pays dividends through faster development, fewer errors, and consistent understanding across all agent interactions.

### What to Document

Focus documentation efforts on tools specific to your domain or industry, recently released tools that postdate agent training, complex tools with non-obvious conceptual models, internal or proprietary systems unique to your organization, and tools with poor, scattered, or outdated public documentation.

Skip documentation for standard Unix commands and utilities, well-established programming language features, widely-adopted frameworks like React, Django, or Rails, and common development tools like Git, Docker, or npm. These tools already exist in agent training data with sufficient depth.

### Creating Effective Documentation

The goal isn't to replicate official documentation but to distill it into efficient, agent-optimized knowledge. Transform verbose documentation into concise patterns that agents can quickly load and apply. A well-crafted mental model document might compress thousands of tokens of HTML documentation into hundreds of tokens of essential patterns and concepts. This distillation process—extracting core concepts from sprawling documentation—creates the token cache that makes `.agent` valuable.

### Structure and Content

Effective tool documentation follows a consistent pattern that helps agents quickly understand and apply the tool.

#### Conceptual Foundation

Begin with the tool's fundamental mental model. Rather than diving into commands, explain the core concepts that make the tool's behavior predictable. For a branching tool, explain how branches relate. For a build system, describe the dependency graph. For an API, clarify the authentication flow and data models.

#### Common Patterns

Document the workflows developers use daily. Show complete examples with context, not just isolated commands. Include the happy path prominently, then cover important variations and edge cases. Real examples with actual file paths and realistic data prove more valuable than abstract descriptions.

#### Error Recovery

Catalog common failure modes and their solutions. When tools fail in predictable ways, documented solutions prevent agents from getting stuck. Include specific error messages, their causes, and step-by-step recovery procedures.

#### Authoritative Resources

Provide direct links to official documentation, preventing agents from finding outdated or incorrect information through general web searches. Link to specific sections of documentation rather than just homepages.

### Creating Documentation

Documentation can emerge from several sources. For open-source tools, clone the repository and extract documentation directly, transforming verbose HTML documentation into concise markdown focused on practical usage. As your team discovers patterns through usage, capture them immediately—when an agent spends significant time understanding a tool's behavior, that understanding becomes valuable documentation for future sessions. When agents search tool documentation online, save useful findings and transform search results into structured documents, removing redundancy and organizing for quick reference.

### Integration Strategies

Make tool documentation discoverable and loadable when needed. Structure documents to support incremental loading—a quick reference for common operations, detailed patterns for complex workflows, and troubleshooting guides for error handling. In your main agent documentation, reference tool documents clearly so agents know when to load additional context.

### Practical Example

Consider documenting Graphite, a specialized stacking tool for Git. Rather than assuming agents understand its unique approach to branch management, create a distilled mental model document at `.agent/tools/graphite.md`:

```markdown
# Graphite (gt) Mental Model

## Core Concept

Graphite manages "stacks"—linear chains of dependent branches...

# ... conceptual overview continues ...

## Common Operations

Creating a stack:

- `gt create feature-1` creates first branch in stack
- `gt create feature-2` stacks on top of feature-1

# ... additional operations ...

## Error Recovery

When "parent branch not found" appears, run `gt sync`...

# ... more error scenarios and solutions ...
```

This document provides enough context for agents to work effectively without searching for documentation or making incorrect assumptions based on Git's branching model. The focus remains on evergreen concepts unlikely to change between minor versions, ensuring documentation longevity.

See `../.agent/tool.github.md` in this repository for an example of tool mental model documentation.

### Maintenance Considerations

Tool documentation requires ongoing attention. Focus on documenting stable, conceptual foundations rather than version-specific details. Update when tools introduce major conceptual changes, not minor feature additions. Refine based on patterns that prove useful in practice. Verify that external documentation links remain valid.

The goal isn't comprehensive coverage but practical sufficiency. Document the core knowledge that enables productive work, leaving detailed reference material to official documentation.

---

## Planning: Iterative Design Before Implementation

### Core Principle

Invest in planning before implementation for non-trivial or complex tasks. Well-crafted plans save time and reduce context thrashing during execution. Think of plans as execution blueprints—detailed specifications that enable efficient, autonomous agent work.

### Key Pattern: Plans as Persistent Documents

For tasks requiring substantial implementation time, persist plans as `.md` files. This approach preserves context across multiple agent sessions, enables switching between planning models and execution models, tracks progress through complex multi-step implementations, and creates clear boundaries between design thinking and implementation.

### Planning Best Practices

#### Iterate on the Plan

Plans often require refinement. Investing in precise planning saves significant implementation time. Fixing errors in plans costs far less than fixing errors in implementations. Treat the planning phase as an opportunity to explore edge cases, identify dependencies, and clarify ambiguities before committing to code.

#### Persist Non-Trivial Plans

Create persistent plans for substantial tasks. Persistent plans preserve context without requiring re-explanation to agents. They provide session flexibility, allowing you to switch between agents or models mid-task. Progress becomes visible through clear checklists of completed work. The original intent remains accessible for debugging when implementation diverges from design.

#### Keep Plans Out of Version Control

In our experience, plans should remain outside repositories. They confuse human reviewers who encounter implementation details in pull requests. Plans also become outdated quickly, creating maintenance burden without corresponding value.

#### Two-Phase Planning for Complex Features

Features touching multiple components or requiring architectural decisions benefit from a two-phase approach.

**Phase 1: Specification Document** focuses on what and why. Create an overview without implementation details. Define functional requirements, constraints, and security considerations. Design APIs with clear interfaces and data flows. Document architecture decisions with rationale, alternatives considered, and accepted tradeoffs.

**Phase 2: Implementation Plan** focuses on how. Create a pre-implementation checklist covering dependencies, environment setup, and documentation review. Develop step-by-step implementation sequences with specific files and patterns. Identify context requirements including files to load, patterns to follow, and external documentation. Define testing strategy spanning unit, integration, and performance benchmarks.

This separation enables using different tools optimized for each phase, reduces cognitive load during implementation, and creates clear decision documentation before coding begins.

---

## Advanced: Custom Tooling

This section covers advanced patterns for creating custom development tooling that amplifies agentic programming capabilities. These patterns represent sophisticated approaches that may require additional infrastructure or investment but provide substantial returns in agent effectiveness.

### Dev-Only CLIs: Flat Script Architecture

#### Core Principle

Organize development CLIs as flat collections of self-contained scripts rather than hierarchical command structures. Each command becomes an independent PEP 723 script with inline dependencies, eliminating complex inheritance hierarchies and shared state management. This pattern transforms CLI development from navigating command trees to working with discrete, disposable scripts that align well with agent capabilities.

#### The Problem with Traditional CLI Architectures

Traditional CLI tools often feature deep command hierarchies, shared utilities, and complex dependency injection patterns. A command might inherit from base classes, import shared utilities, and rely on application-wide configuration. Understanding any single command requires loading multiple files and tracing through inheritance chains—expensive operations for agents working within limited context windows.

Consider a traditional structure:

```
cli/
├── base.py           # Base command class
├── utils/            # Shared utilities
│   ├── auth.py
│   ├── config.py
│   └── formatting.py
├── commands/
│   ├── deploy/
│   │   ├── __init__.py
│   │   ├── base.py     # Deploy base class
│   │   ├── aws.py      # Inherits from deploy base
│   │   └── azure.py    # Also inherits from deploy base
│   └── test/
│       ├── __init__.py
│       └── runner.py   # Uses utils.config, utils.formatting
```

To understand `aws.py`, an agent must load the deploy base class, the global base class, and potentially multiple utility modules. The context requirements compound quickly.

#### Key Pattern: Flat Script Lists

The flat script architecture eliminates hierarchy entirely. Each command lives as a self-contained script with its own dependencies declared inline:

```
commands/
├── deploy-aws/
│   ├── command.py    # Thin Click wrapper
│   └── script.py     # Self-contained PEP 723 script
├── deploy-azure/
│   ├── command.py    # Thin Click wrapper
│   └── script.py     # Self-contained PEP 723 script
├── run-tests/
│   ├── command.py    # Thin Click wrapper
│   └── script.py     # Self-contained PEP 723 script
└── clean-cache/
    ├── command.py    # Thin Click wrapper
    └── script.py     # Self-contained PEP 723 script
```

Each `script.py` is a complete, runnable program:

```python
#!/usr/bin/env python3
# /// script
# dependencies = [
#   "click>=8.1.7",
#   "boto3>=1.34.0",
# ]
# requires-python = ">=3.13"
# ///
"""Deploy application to AWS."""

# pyright: reportMissingImports=false

import subprocess
from pathlib import Path

import boto3
import click


@click.command()
@click.option("--region", default="us-east-1")
def main(region: str) -> None:
    """Complete deployment logic in one file."""
    # All implementation here - no imports from ../utils
    # No inheritance from base classes
    # No shared state or configuration
    pass


if __name__ == "__main__":
    main()
```

#### Why This is Agent-Friendly

The flat script pattern aligns perfectly with how agents process and generate code, creating multiple compounding advantages.

##### Complete Context in One File

When an agent needs to understand or modify a command, everything exists in a single file. No inheritance chains to trace, no utility modules to locate, no shared configuration to understand. The agent loads one file and has complete understanding. This approach enables agents to accomplish more within their context limits.

##### Disposability Without Cleanup

Failed experiments or deprecated commands require only deleting a directory. No untangling of shared dependencies, no checking what else might break, no cleanup of orphaned utilities. This disposability encourages rapid experimentation—agents can try bold approaches knowing that failure costs nothing.

##### Parallel Development at Scale

Since scripts share no code, multiple agents can develop commands simultaneously without coordination. Agent A can rewrite `deploy-aws` while Agent B creates `run-benchmarks` and Agent C refactors `clean-cache`. These parallel efforts avoid conflicts because the scripts remain independent. This enables true parallel development without merge conflicts or integration challenges.

##### Dependencies as Documentation

PEP 723 inline dependencies make requirements explicit and visible:

```python
# /// script
# dependencies = [
#   "httpx>=0.24.0",      # For API calls
#   "rich>=13.0.0",       # For terminal output
#   "pyyaml>=6.0",        # For config parsing
# ]
# ///
```

An agent immediately sees what external libraries are available without searching through requirements files or understanding virtual environment configurations. The dependencies become part of the script's documentation.

#### Implementation with devclikit

The pattern is implemented using a two-file structure per command:

**command.py** - Thin CLI wrapper:

```python
"""Deploy to AWS command."""

from pathlib import Path

import click

from devclikit import run_pep723_script


@click.command(name="deploy-aws")
@click.option("--region", default="us-east-1", help="AWS region")
@click.option("--dry-run", is_flag=True, help="Simulate deployment")
def command(region: str, dry_run: bool) -> None:
    """Deploy application to AWS.

    Examples:
        erk-dev deploy-aws
        erk-dev deploy-aws --region us-west-2
        erk-dev deploy-aws --dry-run
    """
    script_path = Path(__file__).parent / "script.py"

    args = ["--region", region]
    if dry_run:
        args.append("--dry-run")

    run_pep723_script(script_path, args)
```

**script.py** - Self-contained implementation:

```python
#!/usr/bin/env python3
# /// script
# dependencies = [
#   "click>=8.1.7",
#   "boto3>=1.34.0",
# ]
# requires-python = ">=3.13"
# ///
"""AWS deployment implementation."""

# pyright: reportMissingImports=false

# Complete implementation here
# No imports from parent package
# No shared utilities
# Fully self-contained
```

The `command.py` file merely defines the CLI interface and delegates to `script.py`. All logic lives in the script, maintaining complete independence.

#### Practical Example: erk-dev

The `erk-dev` CLI demonstrates this pattern effectively. Each developer tool is a standalone script:

- **codex-review**: Performs AI-powered code review with Graphite integration
- **clean-cache**: Removes temporary files and caches
- **publish-to-pypi**: Handles package publication
- **create-agents-symlinks**: Manages agent documentation symlinks
- **completion**: Generates shell completions

Each command can be understood, modified, or replaced without affecting others. An agent working on improving code review never needs to understand package publication. This isolation enables focused, efficient development.

#### When to Apply This Pattern

Use flat script architecture for:

- **Development-only tools** that don't ship to production
- **Maintenance scripts** and administrative utilities
- **Build and deployment automation** where each target is independent
- **Testing utilities** that run different test suites or benchmarks
- **Code generation tools** that create different types of output

The pattern may not suit:

- **Production CLIs** where code reuse provides user-facing consistency
- **Complex applications** with genuine shared business logic
- **Performance-critical tools** where duplication impacts execution

#### Best Practices

##### Embrace Duplication Over Abstraction

If multiple scripts need similar functionality, copy the code rather than creating shared utilities. Ten lines of duplication costs less than one line of inappropriate abstraction. Agents can easily modify duplicated code but struggle with tangled dependencies.

```python
# In deploy-aws/script.py
def validate_environment():
    """Check AWS credentials and configuration."""
    # 20 lines of validation logic

# In deploy-azure/script.py
def validate_environment():
    """Check Azure credentials and configuration."""
    # Similar 20 lines, adapted for Azure
    # Avoid creating shared_validation.py
```

##### Keep Scripts Focused

Each script should do one thing well. If a script grows beyond 500 lines, consider splitting it into multiple commands rather than extracting shared utilities. Two focused 300-line scripts beat one 600-line script with extracted helpers.

##### Document Dependencies

Use inline comments to explain non-obvious dependency choices:

```python
# /// script
# dependencies = [
#   "click>=8.1.7",          # CLI framework
#   "httpx>=0.24.0",         # Async HTTP client (requests doesn't support HTTP/2)
#   "structlog>=23.0.0",     # Structured logging for debugging
# ]
# ///
```

##### Test Scripts Independently

Since each script stands alone, test it in isolation:

```python
def test_deploy_aws_dry_run():
    """Test AWS deployment in dry-run mode."""
    result = subprocess.run(
        ["uv", "run", "commands/deploy-aws/script.py", "--dry-run"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Dry run completed" in result.stdout
```

#### Integration with Other Patterns

The flat script architecture amplifies other agentic programming patterns:

**Coarse-grained Parallel Modules**: Each script embodies the principle of feature isolation. Scripts are the ultimate coarse-grained module—completely independent and safely disposable.

**Agent Documentation**: Script-specific documentation can live directly in the script file as module docstrings and inline comments, eliminating the need for separate documentation that might drift.

**Planning**: Implementation plans can specify exactly which script to create or modify, with confidence that changes won't cascade through shared dependencies.

**Parallel Development**: Multiple agents can work on different scripts simultaneously, using worktrees to isolate their changes without any risk of conflicts.

#### The Compound Effect

The benefits of flat script architecture compound over time. Initial development is faster because agents don't need to understand existing architecture. Maintenance is simpler because each script can be updated independently. Deprecation is clean because removal leaves no orphaned code. The codebase remains approachable even as it grows, since complexity doesn't increase with script count.

Most importantly, this pattern reduces cognitive load for both humans and agents. A developer can understand any command by reading one file. An agent can modify any command within a single context window. This simplicity enables more ambitious automation and more reliable agent assistance.

#### Anti-Pattern: Premature Abstraction

Avoid extracting shared utilities even when patterns emerge:

```python
# ❌ WRONG - Creating shared utilities too early
# commands/utils/validation.py
def validate_cloud_credentials(provider: str): ...

# commands/deploy-aws/script.py
from ..utils.validation import validate_cloud_credentials

# ✅ CORRECT - Keep validation in each script
# commands/deploy-aws/script.py
def validate_aws_credentials(): ...

# commands/deploy-azure/script.py
def validate_azure_credentials(): ...
```

The moment you create shared utilities, you couple the scripts together. Future changes must consider all consumers. Agents must load multiple files. The simplicity that makes the pattern valuable disappears. Resist the urge to abstract until the duplication genuinely hurts maintainability—and even then, question whether the pain justifies the complexity.

### Parallel Development with Worktrees and Erk

#### Core Principle

Git worktrees enable truly parallel agentic development by creating independent working directories from a single repository. When combined with comprehensive planning and proper orchestration tools, agents can work autonomously on separate features without coordination overhead. This pattern transforms sequential development into parallel execution.

#### Understanding Git Worktrees

Git worktrees solve a fundamental problem in parallel development: the need for multiple working copies without repository duplication. A worktree is a linked working directory that shares the same Git repository but maintains its own working files, index, and HEAD. This means you can have multiple branches checked out simultaneously in different directories, all connected to the same `.git` repository.

Each worktree provides a complete, independent working directory. Agents operating in different worktrees can work simultaneously without conflicts, check out different branches independently, and maintain separate build states and dependencies. Since agents are stateless between sessions, each worktree becomes a persistent workspace for a specific task. An agent can return to its worktree and resume work without needing to understand the state of other parallel efforts.

#### Erk: Orchestrating Parallel Development

While Git provides worktree functionality natively through commands like `git worktree add`, managing multiple worktrees for parallel development introduces complexity. Erk provides an orchestration layer that simplifies worktree lifecycle management, standardizes naming and organization conventions, and integrates planning documents with worktrees automatically.

The tool addresses specific pain points in parallel development: tracking which worktree corresponds to which feature, maintaining consistent branch naming across worktrees, and ensuring plan documents are available in the working directory. By providing consistent commands and conventions, Erk ensures that agents can reliably create, navigate, and manage parallel development environments.

#### Key Pattern: Plan-Based Development

Parallel agent work requires comprehensive planning. Without detailed plans, agents cannot operate autonomously for extended periods. Plan-based development creates a contract between the human architect and the executing agents. When you use `erk create --from-plan`, the tool automatically copies your plan document into the worktree as `.PLAN.md`. This file is gitignored but remains accessible to agents and tools, providing immediate context for the task at hand.

#### Erk Best Practices

##### Keep the Root Repository Clean

When using this planning workflow in erk, the root repository should never have direct commits. It serves as the coordination point and planning center. This approach prevents conflicts between planning and execution, maintains a clean workspace for creating new plans, and ensures the root always reflects the main branch state.

```bash
# Create plans in root, execute in worktrees
cd ~/repository/main
echo "Implementation plan..." > plans/new-feature.md
erk create --from-plan plans/new-feature.md new-feature

# It's best to avoid making changes directly in root
# Prefer not to checkout branches or edit files in the root directory
```

##### Use Plan Files as Task Manifests

Plan files serve as executable specifications for agents containing clear success criteria, specific implementation steps, required context and dependencies, and testing requirements. Think of them as detailed instructions that an agent can follow autonomously. The more comprehensive the plan, the longer an agent can work without human intervention.

##### Leverage Plan-Based Worktree Creation

Erk's `--plan` flag automates the workflow of creating a worktree with embedded context:

```bash
erk create --from-plan plans/auth-feature.md auth-feature
```

This command creates a new worktree for the feature, copies the plan to `.PLAN.md` in the worktree, checks out a new branch, and provides agents with immediate context. The `.PLAN.md` file is gitignored but accessible to tools, allowing agents to understand their mission without additional context.

#### Enabling Autonomous Agent Operation

For parallel development to work effectively, agents must operate autonomously for extended periods. This requires comprehensive planning before execution, clear boundaries between features, and well-defined success criteria. The time invested in creating detailed plans reduces coordination overhead and increases development velocity.

#### Practical Example: Parallel Feature Development

Consider developing three independent features simultaneously:

```bash
# In the root repository, create three plans
echo "User authentication implementation plan..." > plans/user-auth.md
echo "API v2 migration plan..." > plans/api-v2.md
echo "Performance optimization plan..." > plans/perf-opt.md

# Create worktrees with embedded plans
erk create --from-plan plans/user-auth.md user-auth
erk create --from-plan plans/api-v2.md api-v2
erk create --from-plan plans/perf-opt.md perf-opt

# Three agents can now work in parallel
# Agent 1: cd user-auth && implement based on .PLAN.md
# Agent 2: cd api-v2 && implement based on .PLAN.md
# Agent 3: cd perf-opt && implement based on .PLAN.md
```

Each agent operates independently, following its plan without needing to coordinate with others. When features are complete, they can be reviewed and merged independently.

#### Managing Worktree Lifecycle

Worktrees should be treated as temporary workspaces. Once a feature is merged, remove its worktree to keep the development environment clean:

```bash
# After merging the authentication feature
erk delete user-auth

# List active worktrees to review parallel work
erk list
```

This lifecycle management prevents accumulation of stale worktrees and maintains clarity about active development efforts.

#### Anti-Pattern: Underspecified Parallel Work

Attempting parallel development without comprehensive planning typically leads to confusion, conflicts, and wasted effort. Without detailed plans, agents cannot work autonomously. They require constant clarification, defeating the purpose of parallel development. They might also make conflicting assumptions, creating integration challenges later.

#### Integration with Planning Workflow

The worktree pattern integrates seamlessly with the planning practices described earlier. Plans created during the design phase become the execution blueprints for worktrees. This creates a natural flow from conception to completion: planning phase to create detailed plans in the root repository, worktree creation using plan documents to initialize workspaces, parallel execution with multiple agents working autonomously, integration of completed features independently, and cleanup by removing worktrees after successful integration.

This workflow scales to support as many parallel efforts as you have agents available, limited only by the quality of your planning and the independence of your features.

---

## Test Architecture: Coarse-Grained Dependency Injection

### Core Principle

Structure tests using **coarse-grained dependency injection** - wrap entire categories of external operations into injectable dependencies with stateful fake implementations. Rather than mocking individual functions or methods, group related operations together and provide three implementations: Real, Dry-Run, and Fake. This coarse granularity matches how agents think about systems, enables efficient test authoring, and maintains clear boundaries between test setup and execution.

### Why Coarse-Grained?

The key insight is granularity. Fine-grained mocking (individual functions, specific calls) creates fragile tests that require deep implementation knowledge. Coarse-grained injection (entire operational categories) creates robust tests that remain stable as implementations evolve.

```python
# Fine-grained (fragile, hard for agents to understand)
mock_subprocess.run.return_value.stdout = "branch-1\nbranch-2"
mock_path.exists.return_value = True
mock_path.resolve.return_value = Path("/resolved/path")

# Coarse-grained (robust, clear to agents)
fake_git = FakeGitRepository(
    branches=["branch-1", "branch-2"],
    current_branch="branch-1"
)
fake_filesystem = FakeFilesystem(
    existing_files={Path("/resolved/path")}
)
```

### Key Pattern: Category-Based Dependencies

Group operations by the external system they interact with, not by implementation details:

```python
# Category: Version Control Operations
class VersionControl(ABC):
    @abstractmethod
    def list_branches(self) -> list[str]: ...

    @abstractmethod
    def current_branch(self) -> str: ...

    @abstractmethod
    def create_branch(self, name: str) -> None: ...

# Category: Data Persistence
class DataStore(ABC):
    @abstractmethod
    def save_record(self, record: dict) -> str: ...

    @abstractmethod
    def find_records(self, query: dict) -> list[dict]: ...

# Category: External Service Communication
class NotificationService(ABC):
    @abstractmethod
    def send_email(self, to: str, subject: str, body: str) -> None: ...

    @abstractmethod
    def send_sms(self, to: str, message: str) -> None: ...
```

Each category becomes a single dependency that can be injected as a unit. This creates natural boundaries that make sense to both humans and agents.

### The Three Implementations Pattern

Every category of operations should have three implementations:

1. **Real** - Actual implementation for production
2. **Dry-Run** - Safe wrapper that simulates writes but performs reads
3. **Fake** - In-memory implementation with injectable state for testing

```python
# Real: Actual implementation
class GitVersionControl(VersionControl):
    def list_branches(self) -> list[str]:
        result = subprocess.run(["git", "branch"], ...)
        return parse_branches(result.stdout)

# Dry-Run: Safe exploration
class DryRunVersionControl(VersionControl):
    def __init__(self, wrapped: VersionControl):
        self._wrapped = wrapped

    def list_branches(self) -> list[str]:
        return self._wrapped.list_branches()  # Read operations: pass through

    def create_branch(self, name: str) -> None:
        print(f"[DRY RUN] Would create branch: {name}")  # Write operations: simulate

# Fake: Testable with injectable state
class FakeVersionControl(VersionControl):
    def __init__(self, branches: list[str] | None = None):
        self.branches = branches or ["main"]

    def list_branches(self) -> list[str]:
        return self.branches.copy()

    def create_branch(self, name: str) -> None:
        self.branches.append(name)
```

### Organizing Dependencies

How you organize and inject these dependencies depends on your architecture. The key is consistency and explicit state visibility.

**Option 1: Direct Constructor Injection**

```python
class ApplicationService:
    def __init__(self, vcs: VersionControl, store: DataStore):
        self.vcs = vcs
        self.store = store
```

**Option 2: Context Objects**

```python
@dataclass
class AppContext:
    version_control: VersionControl
    data_store: DataStore
    notifications: NotificationService
```

**Option 3: Factory Pattern**

```python
class DependencyFactory:
    def create_dependencies(self, test_mode: bool = False):
        if test_mode:
            return self._create_fakes()
        return self._create_real()
```

Choose the pattern that fits your codebase. The value lies in the coarse granularity and stateful fakes, not the specific injection mechanism.

### Creating Effective Fakes with Injectable State

The power of this pattern emerges from constructor-based state injection. Fakes accept their entire state at construction time, making test scenarios explicit and visible:

```python
class FakeDataStore(DataStore):
    def __init__(self,
                 records: list[dict] | None = None,
                 error_on_save: bool = False,
                 save_latency_ms: int = 0):
        """All state injected at construction for test clarity."""
        self.records = records or []
        self.error_on_save = error_on_save
        self.save_latency_ms = save_latency_ms
        self.saved_records = []  # Track operations for assertions

    def save_record(self, record: dict) -> str:
        if self.error_on_save:
            raise ConnectionError("Database unavailable")

        if self.save_latency_ms:
            time.sleep(self.save_latency_ms / 1000)

        record_id = str(uuid.uuid4())
        self.records.append({**record, "id": record_id})
        self.saved_records.append(record)  # For test assertions
        return record_id
```

This approach makes test intent crystal clear:

```python
def test_handles_database_errors():
    # Explicit state injection - intent is obvious
    fake_store = FakeDataStore(error_on_save=True)
    service = ApplicationService(FakeVersionControl(), fake_store)

    with pytest.raises(ConnectionError):
        service.process_data({"value": 42})

def test_concurrent_saves():
    # Complex scenario still clear through constructor state
    fake_store = FakeDataStore(
        records=[{"id": "1", "value": "existing"}],
        save_latency_ms=100
    )
    # Test proceeds with predictable behavior
```

### Testing CLI Commands

Standard pattern for command testing with dependency injection:

```python
def test_command_behavior() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # 1. Set up filesystem state
        cwd = Path.cwd()
        (cwd / ".git").mkdir()

        # 2. Configure fakes with state
        git = FakeVersionControl(branches=["main", "feature"])
        store = FakeDataStore(records=[{"id": "1", "name": "test"}])

        # 3. Create context with dependencies
        context = AppContext(
            version_control=git,
            data_store=store,
            notifications=FakeNotificationService()
        )

        # 4. Invoke command with context
        result = runner.invoke(cli, ["command", "args"], obj=context)

        # 5. Assert on result
        assert result.exit_code == 0
        assert "expected output" in result.output
```

### Testing Dry-Run Behavior

Verify dry-run prevents destructive operations:

```python
def test_dry_run_does_not_delete() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        # Create resource that should NOT be deleted
        important_file = Path.cwd() / "important.txt"
        important_file.write_text("data")

        # Wrap fake with dry-run
        filesystem = DryRunFilesystem(FakeFilesystem())

        context = AppContext(
            version_control=FakeVersionControl(),
            filesystem=filesystem
        )

        result = runner.invoke(cli, ["delete", "important.txt"], obj=context)

        # Verify dry-run message printed
        assert "[DRY RUN]" in result.output
        # Verify file still exists
        assert important_file.exists()
```

### Benefits for Agentic Development

This pattern specifically addresses agent constraints and capabilities:

**Context Window Efficiency**: Agents can understand the entire test setup from constructor parameters without tracing through mock configurations.

**Pattern Recognition**: The consistent three-implementation pattern lets agents quickly identify which variant to use in which situation.

**Autonomous Test Creation**: With stateful fakes, agents can create comprehensive test scenarios without understanding implementation details.

**Safe Exploration**: Dry-run implementations let agents test destructive operations without system damage.

**Fast Feedback Loops**: Unit tests with fakes run in milliseconds, enabling agents to iterate quickly while integration tests verify actual system behavior.

### When to Apply This Pattern

Use coarse-grained dependency injection when:

- Your code has external dependencies (filesystem, network, databases)
- You need fast, reliable tests
- Agents will be writing or modifying tests
- You want to support dry-run modes for safety

The pattern may be overkill for:

- Pure computational functions without external dependencies
- Simple scripts with minimal testing needs
- Prototypes where test infrastructure investment isn't justified

### Integration with Other Patterns

This testing architecture complements other agentic programming patterns:

**Coarse-grained Parallel Modules**: Each module can have its own set of fake implementations, maintaining the independence that makes parallel development possible.

**Planning**: Test strategies become part of implementation plans, with specific guidance on which fakes to use for different scenarios.

**Agent Documentation**: Document common fake configurations and testing patterns in `.agent/docs/TESTING.md` for reuse across sessions.

### Summary

Coarse-grained dependency injection with stateful fakes creates a testing architecture that both humans and agents can work with effectively. By grouping related operations into injectable categories and providing Real, Dry-Run, and Fake implementations, you enable fast tests, safe exploration, and autonomous agent test authoring. The coarse granularity matches how agents conceptualize systems, while constructor-based state injection makes test intent explicit and maintainable.

---

## Authoring Guidelines

This section provides guidance for maintaining and extending this document. Following these guidelines ensures consistency and readability.

### Tone and Voice

#### Professional and Informative

Write clearly and directly without unnecessary dramatization. Trust that clear, straightforward language conveys importance better than emphatic words. Present information objectively and assume technical competence—intelligent readers don't need ideas shouted at them.

Show patterns through examples rather than prescriptive commands. Instead of declaring what readers must never do, demonstrate better alternatives and explain their benefits. Let the quality of the solution speak for itself.

### Structure and Format

#### Section Organization

Each major section should follow a consistent pattern. Begin with a core principle that summarizes the main idea in one paragraph. Present the key pattern or primary implementation approach. Provide detailed explanation of how and why it works. Include concrete examples that demonstrate the pattern in practice. Address anti-patterns by showing what to avoid and explaining why.

#### Heading Hierarchy

Reserve `#` for the document title only. Use `##` for major sections that appear in the table of contents. Apply `###` for subsections within major sections. Deploy `####` for specific topics within subsections when needed.

#### Code Examples

Provide practical, contextualized examples that readers can understand and adapt:

```python
# Complete example with context
def search_content(query: str, filters: dict) -> list:
    """Search content with optional filters."""
    results = index.search(query)
    if filters:
        results = apply_filters(results, filters)
    return results
```

Prefer complete examples over fragments that lack context or require additional explanation to understand their purpose and integration points.

#### Language-Agnostic When Possible

Use generic examples that apply across languages when illustrating structural patterns. When language-specific examples become necessary, clearly indicate the language and explain any language-specific considerations.

#### Balance Between Abstract and Concrete

Start with the concept to establish understanding. Provide concrete examples that demonstrate real implementations. Return to abstraction to summarize how readers can apply the pattern broadly. This progression from concept to example to principle helps readers both understand and generalize the pattern.
