# dot-agent-kit

Kit management system for Claude Code.

## Package vs CLI

- **Package name**: `dot-agent-kit` (what you install)
- **CLI command**: `erk` (what you run)

This naming follows the convention where the package name describes what it provides (a kit management system), while the CLI command is concise for frequent use.

## Installation

```bash
uv pip install dot-agent-kit
```

Or with pip:

```bash
pip install dot-agent-kit
```

## Usage

After installation, use the `erk` command:

```bash
# Initialize configuration
erk init

# View available commands
erk --help

# Manage kits
erk kit install <kit-name>
erk kit list
```

## Creating Kits

### Understanding Command Types

There are two distinct types of commands in the kit system:

1. **Slash commands** - Markdown files (`.md`) invoked in Claude Code with `/command-name`
   - Defined in `.claude/commands/` directory (after installation)
   - Stored in `commands/` directory within the kit
   - Listed in `kit.yaml` under `artifacts.command`
   - Expand to prompts when invoked
   - Example: `/gt:submit-branch`

2. **Kit cli commands** - Python executables (`.py`) invoked via CLI with `erk kit exec kit-id command-name`
   - Stored in `kit_cli_commands/` directory within the kit
   - Listed in `kit.yaml` under `kit_cli_commands`
   - Defined in kit directories as Python scripts
   - Listed in `kit.yaml` under `kit_cli_commands`
   - Execute Python code directly
   - Example: `erk kit exec gt submit-branch`

This distinction is important when creating kits and defining their capabilities in `kit.yaml`.

### Kit Structure

A kit is a collection of Claude Code artifacts (agents, skills, slash commands) distributed as a package. Each kit requires:

1. **kit.yaml** - Manifest file with kit metadata and artifact paths
2. **Artifacts** - The actual agent, skill, and slash command files

### Namespace Pattern (Required)

**All bundled kits** must follow the namespace pattern:

```
{artifact_type}s/{kit_name}/...
```

This organizational pattern:

- Prevents naming conflicts when multiple kits are installed
- Makes it clear which kit an artifact belongs to
- Enables clean uninstallation of kit artifacts
- Keeps the `.claude/` directory organized

**Example structure:**

```
my-kit/
├── kit.yaml
├── agents/
│   └── my-kit/
│       └── my-agent.md
└── skills/
    └── my-kit/
        ├── tool-a/
        │   └── SKILL.md
        └── tool-b/
            └── SKILL.md
```

**Example kit.yaml:**

```yaml
name: my-kit
version: 1.0.0
description: My awesome Claude Code kit
artifacts:
  agent:
    - agents/my-kit/my-agent.md
  skill:
    - skills/my-kit/tool-a/SKILL.md
    - skills/my-kit/tool-b/SKILL.md
  command:
    - commands/my-kit/my-slash-command.md
kit_cli_commands:
  - name: my-cli-command
    path: kit_cli_commands/my-kit/my_cli_command.py
    description: Execute Python CLI command
```

### Invocation Names vs File Paths

**Important**: Claude Code discovers artifacts by their filename/directory name, not the full path:

- **Agents**: Discovered by filename (e.g., `agents/my-kit/helper.md` → invoked as "helper")
- **Skills**: Discovered by directory name (e.g., `skills/my-kit/pytest/SKILL.md` → invoked as "pytest")
- **Slash commands**: Discovered by filename (e.g., `commands/my-kit/build.md` → invoked as "/build")
- **Kit cli commands**: Invoked via CLI (e.g., `erk kit exec my-kit build` for command defined in `kit_cli_commands`)

The namespace directory (`my-kit/`) is **organizational only** - it doesn't become part of the invocation name.

**Hyphenated naming convention (kebab-case)**: ALL artifacts MUST use hyphenated naming (kebab-case), NOT underscores. Use hyphens to combine words (e.g., `skills/devrun-make/SKILL.md` → "devrun-make", `commands/my-command.md` → "/my-command"). This is the standard for ALL Claude artifacts - bundled kits and project-local alike.

**DO NOT use underscores** (`_`) in artifact names. Use hyphens (`-`) instead:

- ✅ CORRECT: `my-command.md`, `api-client/SKILL.md`, `test-runner.md`
- ❌ WRONG: `my_command.md`, `api_client/SKILL.md`, `test_runner.md`

Exception: Python scripts within artifacts may use snake_case (they're code, not artifacts).

### Supporting Documentation

**Supporting documentation** for kits (examples, tutorials, references, etc.) should be stored in:

```
.claude/docs/{kit_id}/
```

This organizational pattern:

- Keeps non-executable documentation separate from the actual artifacts
- Prevents documentation files from appearing as commands
- Provides a clear location for kit-specific documentation
- Maintains organization when multiple kits are installed

**Example structure:**

```
.claude/
├── commands/
│   └── my-kit/
│       └── my-command.md      # Executable command
├── docs/
│   └── my-kit/
│       ├── EXAMPLES.md         # Usage examples
│       ├── TUTORIAL.md         # Tutorial guide
│       └── REFERENCE.md        # API reference
└── skills/
    └── my-kit/
        └── SKILL.md            # Executable skill
```

**Important**: Only place actual executable artifacts (commands, skills, agents) in their respective directories. All supporting documentation, examples, tutorials, and non-executable markdown files should go in `.claude/docs/{kit_id}/`.

### Namespace Standards for Kit Types

**Bundled kits** (distributed with packages): Should follow hyphenated naming convention (e.g., `skills/kit-name-tool/`) to avoid naming conflicts and maintain clear organization.

**Project-local artifacts** (in `.claude/` not from kits): MUST also use kebab-case naming. The hyphenated naming standard applies to ALL artifacts, regardless of whether they're bundled or project-local.

### Adopting Hyphenated Naming

To align with the standard hyphenated naming convention:

1. **Flatten directory structure with hyphenated names:**

   ```bash
   # Example: Convert skills/devrun/make/ to skills/devrun-make/
   mv skills/devrun/make skills/devrun-make
   mv skills/devrun/pytest skills/devrun-pytest
   ```

2. **Update kit.yaml artifact paths:**

   ```yaml
   artifacts:
     skill:
       - skills/devrun-make/SKILL.md # Was: skills/devrun/make/SKILL.md
       - skills/devrun-pytest/SKILL.md # Was: skills/devrun/pytest/SKILL.md
   ```

3. **Test installation** to verify paths are correct

## Adding Bundled Kits

To add a new bundled kit to the dot-agent-kit registry:

1. **Create the kit structure** in `src/dot_agent_kit/data/kits/{kit-name}/`:

   ```
   kits/
   └── my-kit/
       ├── kit.yaml
       ├── kit_cli_commands/
       │   └── my-kit/
       │       └── my_cli_command.py
       ├── commands/
       │   └── my-kit/
       │       └── my-slash-command.md
       ├── agents/
       │   └── my-kit/
       │       └── my-agent.md
       └── skills/
           └── my-kit/
               └── SKILL.md
   ```

2. **Define kit.yaml** with metadata and artifact paths:

   ```yaml
   name: my-kit
   version: 0.1.0
   description: Brief description of what the kit provides
   license: MIT
   artifacts:
     agent:
       - agents/my-kit/my-agent.md
     skill:
       - skills/my-kit/SKILL.md
     command:
       - commands/my-kit/my-slash-command.md # Slash command (markdown)
   kit_cli_commands: # Kit CLI commands (Python executables)
     - name: my-cli-command
       path: kit_cli_commands/my-kit/my_cli_command.py
       description: Execute Python CLI command
   ```

3. **Register the kit** in `src/dot_agent_kit/data/registry.yaml`:

   ```yaml
   - kit_id: my-kit
     name: My Kit
     description: Brief description of what the kit provides
     source: bundled:my-kit
   ```

4. **Test the kit** is discoverable:

   ```bash
   erk kit search
   ```

5. **Install and verify the kit**:

   ```bash
   # Install using the bundled: prefix
   erk kit install bundled:my-kit

   # Verify installation
   erk check
   ```

**Note**: The `source:` field in registry.yaml determines the prefix users must use:

- `source: bundled:my-kit` → install with `erk kit install bundled:my-kit`
- `source: package:my-kit` → install with `erk kit install package:my-kit`

The kit will now appear in the available kits list and can be installed by users.

## Managing Kit Artifacts

Once a kit is created, you can add or remove artifacts (agents, skills, commands, docs) to extend or modify its functionality.

### Adding Artifacts to an Existing Kit

To add a new artifact to a bundled kit:

1. **Create the artifact file** in the appropriate namespace directory:

   ```
   kits/{kit-name}/
   ├── agents/{kit-name}/        # For agents
   ├── skills/{kit-name}/         # For skills
   ├── commands/{kit-name}/       # For slash commands
   ├── docs/{kit-name}/           # For documentation
   └── kit_cli_commands/{kit-name}/  # For CLI commands
   ```

2. **Update kit.yaml** to reference the new artifact:

   For agents, skills, commands, or docs:

   ```yaml
   artifacts:
     agent:
       - agents/{kit-name}/my-agent.md
     skill:
       - skills/{kit-name}/my-skill/SKILL.md
     command:
       - commands/{kit-name}/my-command.md
     doc:
       - docs/{kit-name}/my-doc.md
   ```

   For kit CLI commands:

   ```yaml
   kit_cli_commands:
     - name: my-cli-command
       path: kit_cli_commands/{kit-name}/my_command.py
       description: Brief description
   ```

3. **Test the changes** by reinstalling the kit:

   ```bash
   # Uninstall existing kit
   erk kit uninstall bundled:{kit-name}

   # Reinstall with new artifacts
   erk kit install bundled:{kit-name}

   # Verify installation
   erk check
   ```

### Removing Artifacts from a Kit

To remove an artifact from a bundled kit:

1. **Delete the artifact file** from the kit directory
2. **Remove the entry** from `kit.yaml` (from `artifacts` or `kit_cli_commands` section)
3. **Test the changes** by reinstalling the kit (see above)

### Common Patterns

**Adding an agent:**

- File: `agents/{kit-name}/my-agent.md`
- Entry: `artifacts.agent` list in kit.yaml
- Invoked as: "my-agent" (filename without .md)

**Adding a skill:**

- File: `skills/{kit-name}/my-skill/SKILL.md` (or `skills/my-skill-name/SKILL.md` for flattened structure)
- Entry: `artifacts.skill` list in kit.yaml
- Invoked as: "my-skill" (directory name containing SKILL.md)

**Adding a slash command:**

- File: `commands/{kit-name}/my-command.md`
- Entry: `artifacts.command` list in kit.yaml
- Invoked as: "/my-command" (filename without .md)

**Adding a kit CLI command:**

- File: `kit_cli_commands/{kit-name}/my_command.py`
- Entry: `kit_cli_commands` list in kit.yaml
- Invoked as: `erk kit exec {kit-id} my-cli-command`

**Adding documentation:**

- File: `docs/{kit-name}/my-doc.md`
- Entry: `artifacts.doc` list in kit.yaml
- Referenced by: Skills or agents that need supporting documentation

### Troubleshooting

**Missing artifact after rename:**

This is the most common issue when renaming artifacts.

- **Symptom**: `erk check` shows "Missing artifacts (in manifest but not installed)"
- **Cause**: kit.yaml still references old filename, or kit wasn't reinstalled after rename
- **Fix**:
  1. Update kit.yaml with new artifact path
  2. Force-reinstall kit: `erk kit install bundled:{kit-name} --force`
  3. Verify: `erk check` should show ✅
- **See**: [ARTIFACT_LIFECYCLE.md](docs/ARTIFACT_LIFECYCLE.md#renaming-an-artifact) for complete rename procedure

**Stale symlink:**

- **Symptom**: Symlink exists in `.claude/` but appears broken (red in `ls -la`)
- **Cause**: Source file was renamed/moved but kit wasn't reinstalled
- **Diagnosis**: `readlink .claude/commands/{namespace}/{artifact}.md` points to non-existent file
- **Fix**: Force-reinstall kit to recreate symlinks with correct targets

**Force reinstall required after manifest changes:**

- **When needed**: After any changes to kit.yaml (adding/removing/renaming artifacts)
- **Why**: Symlinks sync file contents automatically, but structural changes require reinstallation
- **How**: `erk kit remove {kit-name}` then `erk kit install bundled:{kit-name} --force`
- **Safe in dev mode**: Symlinks point to source files, so no data is lost

**Command not found after changes:**

- **Symptom**: Artifact appears in `erk artifact list` but invocation fails
- **Possible causes**:
  - Cross-references in other files still use old command name
  - Naming convention violated (must use kebab-case, not snake_case)
  - Namespace incorrect (should match directory structure)
- **Fix**: Update all cross-references, verify kebab-case naming, check namespace matches directory path

**Artifact not appearing after installation:**

- Verify the artifact path in kit.yaml matches the actual file location
- Check that the path is relative to the kit root directory
- Ensure the artifact follows naming conventions (kebab-case, no underscores)

**Kit reinstall fails:**

- Validate kit.yaml syntax with a YAML parser
- Check that all referenced files exist
- Verify namespace directories match kit name

**Artifact conflicts between kits:**

- Ensure each kit uses its own namespace directory (`{kit-name}/`)
- Check for duplicate artifact names across kits
- Review installed artifacts with `erk check`

**Further troubleshooting:**

For detailed procedures on common operations (renaming, deleting, moving artifacts), see [docs/ARTIFACT_LIFECYCLE.md](docs/ARTIFACT_LIFECYCLE.md).
