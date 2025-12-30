# Kit CLI Push Down Pattern

## The Problem with Embedded Scripts

Claude Code skills and slash commands support embedded bash scripts directly in markdown. This seems convenient—you write a script inline and the agent executes it. But this approach has fundamental limitations:

**No execution environment.** Embedded scripts run in whatever shell context the agent happens to be in. There's no virtual environment, no dependency management, no guaranteed Python version. A script that works on one machine may fail on another.

**No testability.** You cannot unit test a bash snippet embedded in markdown. You cannot mock dependencies, assert on edge cases, or verify error handling. The only way to test is to run the agent and hope it works.

**No type safety.** Bash has no types. A typo in a variable name silently produces wrong results. Complex string manipulation with regex varies between shells and fails in subtle ways.

**No reusability.** The same parsing logic gets copy-pasted across multiple commands and skills. When you find a bug, you fix it in one place and forget the others.

**Token overhead.** Every embedded script consumes prompt tokens. Error handling code, edge case logic, and fallback behavior all bloat the prompt—and the agent still has to read and understand it.

## The Push Down Solution

Instead of embedding mechanical computation in prompts, push it down to kit CLI commands—proper Python programs installed as packages.

**Analogy**: Like database query optimizers that "push down" predicates closer to the data layer for efficiency, this pattern moves computation from LLM prompts to Python CLI where it belongs.

### What Kit CLI Commands Provide

**Real Python environment.** Kit CLI commands are installed Python packages with proper dependency management. They run in a known environment with a specific Python version. Dependencies are declared in `pyproject.toml` and installed via `uv`.

**Full testability.** Commands are regular Python functions. You can write unit tests with pytest, mock external services, test edge cases exhaustively, and measure coverage. A command like `issue-title-to-filename` has comprehensive unit tests covering edge cases and boundary conditions.

**Type safety.** Python type hints catch errors before runtime. Dataclasses enforce structured output. The type checker validates that success and error responses have consistent schemas.

**Complexity without chaos.** Because commands are proper Python, you can build sophisticated logic: state machines, parsers, validators, data transformers. The complexity is encapsulated, tested, and hidden from the agent prompt.

**Structured JSON contracts.** Commands return JSON with explicit success/failure indicators. The agent doesn't parse free-form text—it reads structured data with predictable fields.

## The Decision Rule

**If it requires understanding meaning → use LLM. If it's mechanical transformation → use kit CLI.**

| Push to Kit CLI                                     | Keep in Agent                              |
| --------------------------------------------------- | ------------------------------------------ |
| Parsing/validation (URLs, formats, paths)           | Semantic analysis (summarizing, naming)    |
| Data extraction (JSON/YAML, filtering)              | Content generation (docs, code, messages)  |
| Deterministic operations (file queries, transforms) | Complex reasoning (trade-offs, ambiguity)  |
| Token reduction (compressing, pre-filtering)        | Decision-making (planning, interpretation) |

## Before and After

**Before**: Fragile bash embedded in agent prompt, untestable, shell-dependent:

```bash
if [[ "$issue_arg" =~ github\.com/[^/]+/[^/]+/issues/([0-9]+) ]]; then
    issue_number="${BASH_REMATCH[1]}"
elif [[ "$issue_arg" =~ ^[0-9]+$ ]]; then
    issue_number="$issue_arg"
else
    echo "Error: Invalid input format"
    exit 1
fi
```

**After**: Agent invokes tested Python command, reads structured output:

```bash
filename=$(erk exec issue-title-to-filename "$title")
```

The conversion logic lives in Python with proper unit tests. The agent prompt shrinks. Reliability increases.

## The Architectural Win

This pattern separates concerns cleanly:

- **Kit CLI**: Mechanical operations (parsing, validation, file I/O, data transformation)
- **Agent**: Semantic operations (understanding intent, generating content, making decisions)

The agent becomes an orchestrator that delegates deterministic work to tested code. It focuses on what LLMs do well—understanding and generating—while Python handles what programming languages do well—precise, repeatable computation.

## Implementation

For detailed implementation patterns, examples, and checklists, see:
→ [docs/learned/kits/push-down-pattern.md](../../learned/kits/push-down-pattern.md)
