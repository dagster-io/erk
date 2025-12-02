# Agent-Delegating Commands Pattern

## What

Commands that immediately delegate to specialized agents for complete workflow orchestration. These are lightweight wrappers that shell out to agents, declining accumulated conversation context and creating clean execution boundaries.

**Architecture:**

```
Command (lightweight wrapper)
    ↓ delegates to
Agent (orchestration + workflow execution)
    ↓ uses tools to
Complete the workflow
```

The command provides a deterministic entry point - users know exactly what will happen when they invoke it. The agent handles the actual execution with fresh context.

## Why

This pattern addresses three fundamental challenges:

### 1. Context Reduction

Commands immediately delegate to agents, declining accumulated conversation context. This prevents context pollution and keeps workflows focused.

**Problem it solves:** As users interact with the assistant, context accumulates. Long conversations carry irrelevant history that:

- Increases token costs
- Slows execution
- Dilutes focus on the current task
- Can introduce confusion from unrelated context

**Solution:** Immediate delegation creates a clean context boundary. The agent starts with only what it needs to know for the specific workflow.

### 2. Model Selection Flexibility

Different agents can use different models based on their needs. Fast, mechanical workflows can use smaller, faster models for speed and cost efficiency, while complex analysis can use larger, more capable models.

**Value:** The command layer abstracts model selection from the user interface. Users invoke the same command regardless of which model executes the workflow.

### 3. Deterministic User Experience

Commands provide explicit, typed interfaces that users understand and control. Unlike conversational workflows where the assistant might interpret intent differently, commands have clear contracts:

- **Predictable behavior** - Users know exactly what will happen
- **No interpretation ambiguity** - Command invocation is explicit
- **Clear success criteria** - Users can verify outcomes
- **Reliable repeatability** - Same input produces same workflow

This determinism contrasts with more fluid conversational patterns where users may feel uncertain about when or how functionality will activate.

## How It Works

The pattern separates concerns between two layers:

### Command Layer (Thin)

The command is a lightweight entry point that:

- Defines the user-facing interface
- Documents what the workflow does
- Immediately delegates to an agent
- Provides no workflow logic itself

**Characteristics:**

- Short (typically ~40-50 lines including documentation)
- Contains only delegation logic
- Deterministic - always invokes the same agent
- User-facing contract

### Agent Layer (Thick)

The agent handles the complete workflow:

- Contains all orchestration logic
- Makes decisions based on current state
- Coordinates multiple tools and operations
- Handles errors and edge cases
- Formats results for user display

**Characteristics:**

- Can be lengthy (100-400+ lines)
- Contains all workflow complexity
- Executed with fresh context (no conversation history)
- Can be invoked from multiple sources (commands, code, other agents)

## Benefits

### Clear Separation of Concerns

- **Commands define the interface** - What the workflow does and how to invoke it
- **Agents implement the logic** - How the workflow executes step-by-step
- **Users get predictability** - Explicit contracts vs. conversational ambiguity

### Performance Optimization

- **Model selection per workflow** - Fast models for mechanical tasks, powerful models for complex analysis
- **Context efficiency** - Fresh context reduces token costs and speeds execution
- **Parallel execution** - Multiple workflows can run independently without context interference

### Reusability and Composition

- **One agent, many entry points** - Multiple commands can delegate to the same agent
- **Agents can invoke agents** - Complex workflows decompose into specialized sub-workflows
- **Programmatic access** - Code can invoke agents directly without going through commands

### Testing and Reliability

- **Testable contracts** - Commands have clear inputs and expected outputs
- **Isolated workflows** - Agent execution is independent of conversation state
- **Reproducible behavior** - Same invocation produces consistent results
