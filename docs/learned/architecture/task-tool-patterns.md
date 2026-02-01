---
title: Task Tool Patterns and Error Handling
read_when:
  - "using Task tool for subagent delegation"
  - "using TaskOutput to retrieve subagent results"
  - "debugging subagent execution failures"
  - "implementing workflows with background agents"
  - "parsing subagent output"
---

# Task Tool Patterns and Error Handling

## Overview

The Task tool delegates work to specialized subagents. When retrieving results via TaskOutput, always check for errors before accessing the payload to avoid silent failures.

## Core Pattern

### Launching Tasks

```python
# Synchronous (blocking)
Task(
    subagent_type="agent-name",
    description="Brief description",
    prompt="Detailed instructions"
)

# Asynchronous (background)
Task(
    subagent_type="agent-name",
    description="Brief description",
    prompt="Detailed instructions",
    run_in_background=True
)  # Returns task_id
```

### Retrieving Results

**Always parse JSON and check for errors before accessing payload:**

```python
# Get task output
result = TaskOutput(task_id=task_id, block=True)

# Parse JSON
import json
result_data = json.loads(result)

# Check for errors FIRST
if "error" in result_data:
    # Handle error
    error_msg = result_data["error"]
    raise Exception(f"Task failed: {error_msg}")

# Now safe to access payload
payload = result_data["payload"]
# ... use payload ...
```

## Structured Error Checking

### Correct Pattern

```python
# Step 1: Get output
output = TaskOutput(task_id=agent_id, block=True)

# Step 2: Parse JSON
data = json.loads(output)

# Step 3: Check error field
if "error" in data:
    print(f"❌ Error: {data['error']}")
    return

# Step 4: Access payload
result = data["payload"]
```

### Anti-Pattern (Unsafe)

```python
# ❌ WRONG: Direct payload access without error check
output = TaskOutput(task_id=agent_id, block=True)
data = json.loads(output)
result = data["payload"]  # Crashes if error occurred!
```

**Why it fails**: If the subagent encountered an error, `data["payload"]` may not exist, causing a KeyError.

## Error Handling Patterns

### Pattern 1: Early Return on Error

```python
data = json.loads(TaskOutput(task_id=agent_id, block=True))

if "error" in data:
    print(f"❌ Agent failed: {data['error']}")
    return  # Stop workflow

# Continue with successful result
result = data["payload"]
```

### Pattern 2: Try-Except with Fallback

```python
try:
    data = json.loads(TaskOutput(task_id=agent_id, block=True))

    if "error" in data:
        raise Exception(data["error"])

    result = data["payload"]

except Exception as e:
    print(f"❌ Task failed: {e}")
    # Fallback behavior
    result = default_value
```

### Pattern 3: Accumulate Errors from Multiple Agents

```python
errors = []
results = []

for task_id in task_ids:
    data = json.loads(TaskOutput(task_id=task_id, block=True))

    if "error" in data:
        errors.append(data["error"])
    else:
        results.append(data["payload"])

if errors:
    print(f"❌ {len(errors)} tasks failed:")
    for error in errors:
        print(f"  - {error}")
    return

# All tasks succeeded
for result in results:
    process(result)
```

## Common Mistakes

### ❌ Mistake 1: No Error Check

```python
# Direct access without checking for errors
output = TaskOutput(task_id=agent_id)
data = json.loads(output)
result = data["payload"]  # KeyError if agent failed!
```

### ❌ Mistake 2: Checking Wrong Field

```python
# Checking for "status" instead of "error"
if data["status"] != "success":  # Wrong!
    print("Failed")
```

**Correct**: Check for `"error"` key in result dict.

### ❌ Mistake 3: Not Parsing JSON First

```python
# Trying to access fields before parsing JSON
output = TaskOutput(task_id=agent_id)
if output.error:  # Wrong! output is JSON string, not dict
    print("Failed")
```

**Correct**: Parse JSON first, then check dict keys.

## Real-World Examples

### Example 1: Learn Workflow (Multiple Parallel Agents)

```python
# Launch agents
session_id = Task(
    subagent_type="session-analyzer",
    run_in_background=True
)

diff_id = Task(
    subagent_type="code-diff-analyzer",
    run_in_background=True
)

docs_id = Task(
    subagent_type="existing-docs-checker",
    run_in_background=True
)

# Wait and check all agents
agent_ids = [session_id, diff_id, docs_id]
outputs = []

for agent_id in agent_ids:
    output_json = TaskOutput(task_id=agent_id, block=True)
    data = json.loads(output_json)

    if "error" in data:
        print(f"❌ Agent {agent_id} failed: {data['error']}")
        return  # Stop entire workflow on any failure

    outputs.append(data["payload"])

# All agents succeeded, proceed with outputs
session_analysis, diff_analysis, docs_analysis = outputs
```

### Example 2: Plan Synthesis (Single Agent)

```python
# Launch synthesis agent
task_id = Task(
    subagent_type="plan-synthesizer",
    description="Synthesize documentation plan",
    prompt=f"Create plan from: {input_data}"
)

# Wait for result
output = TaskOutput(task_id=task_id, block=True)
data = json.loads(output)

# Check for error
if "error" in data:
    print(f"❌ Synthesis failed: {data['error']}")
    print("Please review input data and try again.")
    return

# Extract plan
plan_content = data["payload"]["plan"]
print(f"✅ Plan created: {len(plan_content)} lines")
```

## Tripwire

**Before accessing `data["payload"]` from TaskOutput, always check `if "error" in data` first.**

Failure to check causes silent crashes when subagents encounter errors.

## Best Practices

1. **Always parse JSON first** - TaskOutput returns JSON string, not dict
2. **Check for errors immediately** - Before accessing any payload fields
3. **Fail fast** - Don't continue workflow if agent failed
4. **Provide context** - Include agent name and task in error messages
5. **Handle multiple agents** - Check each agent's result individually

## Debugging Failed Tasks

If a task fails with unclear error:

1. **Check task logs** - Task may have written to stderr
2. **Inspect agent definition** - Verify frontmatter and tools
3. **Test prompt** - Ensure prompt is complete and self-contained
4. **Verify input data** - Ensure all required context is passed

## Related Patterns

- [Subagent Delegation for Optimization](subagent-delegation-for-optimization.md) - When to use Task tool
- [Subagent Prompt Structure](subagent-prompt-structure.md) - How to structure prompts
- [Agent Delegation](../planning/agent-delegation.md) - Complete delegation workflow
