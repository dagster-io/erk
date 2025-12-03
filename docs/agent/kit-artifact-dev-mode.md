# Adding Kit Artifacts in Dev Mode

This guide covers the complete workflow for adding artifacts (commands, skills, agents, hooks) to bundled kits when working in dev mode (editable install).

## Overview

When developing kits locally (via `uv pip install -e`), symlinks in `.claude/` point to files in your working directory rather than installed packages. Adding new artifacts requires updating multiple locations to ensure proper registration and discoverability.

## Detection: How to Know You're in Dev Mode

You're in dev mode if:

1. **Symlinks in `.claude/` point to local paths**:

   ```bash
   ls -la .claude/commands/
   # Dev mode: points to packages/dot-agent-kit/src/...
   # Installed mode: points to site-packages/...
   ```

2. **Package installed with `-e` flag**:

   ```bash
   uv pip list | grep dot-agent-kit
   # Shows editable install path if in dev mode
   ```

3. **Working in the erk repository** with local package development

## Required Steps

Adding a new artifact to a bundled kit requires **5 steps**:

### Step 1: Create the Artifact File

Create the actual artifact file in the kit's data directory:

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit_name}/{artifact_type}/{artifact_name}.md
```

**Example - Adding a command to the `erk` kit:**

```
packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/my-new-command.md
```

**Artifact types:**

- `commands/` - Slash commands (`.md` files)
- `skills/` - Skills (`.md` files)
- `agents/` - Agent definitions (`.md` files)
- `hooks/` - Hook configurations (`.md` files)

### Step 2: Register in kit.yaml

Add the artifact to the kit's `kit.yaml` file:

```yaml
# packages/dot-agent-kit/src/dot_agent_kit/data/kits/{kit_name}/kit.yaml

commands:
  - name: my-new-command
    path: commands/my-new-command.md
    description: Brief description of what the command does
```

**Important:** The `name` field determines the command/skill name. Use kebab-case.

### Step 3: Create Symlink in `.claude/`

Create a symlink from `.claude/{artifact_type}/` to the artifact file:

```bash
# From repository root
cd .claude/commands
ln -s ../../packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/my-new-command.md my-new-command.md
```

**Symlink paths by artifact type:**

```
.claude/commands/   → commands/*.md
.claude/skills/     → skills/*.md
.claude/agents/     → agents/*.md
.claude/hooks/      → hooks/*.md
```

### Step 4: Update dot-agent.toml

Register the artifact in `dot-agent.toml` at repository root:

```toml
# dot-agent.toml

[project.commands]
my-new-command = ".claude/commands/my-new-command.md"

[project.skills]
# ... existing skills ...

[project.agents]
# ... existing agents ...
```

**Section names:**

- `[project.commands]` for commands
- `[project.skills]` for skills
- `[project.agents]` for agents
- `[project.hooks]` for hooks

### Step 5: Update Test Fixtures (if applicable)

If the kit has test fixtures that enumerate artifacts, update them:

```python
# tests/fixtures/kit_fixtures.py or similar

EXPECTED_ERK_COMMANDS = [
    "existing-command",
    "my-new-command",  # Add new command
]
```

Check for:

- Test files that list expected artifacts
- Snapshot tests of kit contents
- Integration tests that verify artifact counts

## Verification

After completing all steps, verify the setup:

### 1. Check Symlink Resolves

```bash
ls -la .claude/commands/my-new-command.md
# Should show symlink pointing to kit data directory
```

### 2. Verify Kit Registration

```bash
dot-agent kit list
# Should show the kit with the new artifact
```

### 3. Test Command Discovery

```bash
# In Claude Code
/my-new-command
# Should be discoverable and executable
```

### 4. Run Tests

```bash
uv run pytest tests/ -k "kit"
# Ensure no fixture mismatches
```

## Common Pitfalls

### Pitfall 1: Missing Symlink

**Symptom:** Command not found in Claude Code, but `dot-agent kit list` shows it

**Fix:** Create the symlink in `.claude/{artifact_type}/`

### Pitfall 2: Wrong Symlink Path

**Symptom:** Symlink exists but points to wrong location or broken

**Fix:** Remove and recreate with correct relative path:

```bash
rm .claude/commands/my-new-command.md
cd .claude/commands
ln -s ../../packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/my-new-command.md my-new-command.md
```

### Pitfall 3: Missing dot-agent.toml Entry

**Symptom:** Command works via kit but not as project command

**Fix:** Add entry to appropriate section in `dot-agent.toml`

### Pitfall 4: Naming Mismatch

**Symptom:** Command registered but not callable by expected name

**Fix:** Ensure `name` in kit.yaml matches filename (minus extension) and symlink name

### Pitfall 5: Forgot kit.yaml Registration

**Symptom:** File exists but kit doesn't know about it

**Fix:** Add entry to kit.yaml with name, path, and description

## Complete Example

Adding a new command `plan-status` to the `erk` kit:

```bash
# Step 1: Create the file
cat > packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/plan-status.md << 'EOF'
# /plan-status

Show the current status of the implementation plan.

## Instructions

Read `.impl/progress.md` and display current step status.
EOF

# Step 2: Add to kit.yaml
# Edit packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/kit.yaml
# Add under commands:
#   - name: plan-status
#     path: commands/plan-status.md
#     description: Show current implementation plan status

# Step 3: Create symlink
cd .claude/commands
ln -s ../../packages/dot-agent-kit/src/dot_agent_kit/data/kits/erk/commands/plan-status.md plan-status.md
cd ../..

# Step 4: Update dot-agent.toml
# Add under [project.commands]:
# plan-status = ".claude/commands/plan-status.md"

# Step 5: Verify
ls -la .claude/commands/plan-status.md
dot-agent kit list
```

## Related Documentation

- [kit-cli-commands.md](kit-cli-commands.md) - Python/LLM boundary for kit CLI commands
- [kit-code-architecture.md](kit-code-architecture.md) - Two-layer kit architecture
