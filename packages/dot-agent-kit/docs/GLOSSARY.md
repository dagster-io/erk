# dot-agent-kit Glossary

## Core Concepts

### Artifact

A file that extends Claude Code functionality. Artifacts live in `.claude/` directories and come in five types:

- **Skill**: Specialized knowledge or workflow guidance (`.claude/skills/`)
- **Command**: Slash command that expands to a prompt (`.claude/commands/`)
- **Agent**: Autonomous subprocess for complex tasks (`.claude/agents/`)
- **Hook**: Executable script triggered by events (`.claude/hooks/`)
- **Doc**: Reference documentation (`.claude/docs/`)

### Kit

A packaged collection of related artifacts that can be installed, updated, and removed as a unit. Kits are tracked in `installed.toml` and can include any combination of artifact types.

### Artifact Source

Artifacts have one of two sources:

#### MANAGED

- Installed from a kit
- Tracked in `installed.toml` under `[kits.<kit-id>].artifacts`
- Has `kit_id` and `kit_version` metadata
- Updated/removed via kit commands
- Example: A skill installed via `erk kit install devrun`

#### LOCAL

- Created manually by the user
- Not associated with any kit
- Not tracked in `installed.toml`
- Managed individually, not as part of a kit
- Example: A custom command created via `erk artifact create command my-cmd`

### Artifact Level

Artifacts can be installed at two levels:

#### USER Level

- Global artifacts in `~/.claude/`
- Available to all projects for the current user
- Useful for personal preferences and frequently used artifacts

#### PROJECT Level

- Project-specific artifacts in `./.claude/`
- Only available within the current project
- Useful for team-shared configurations and project-specific workflows

## Configuration

### installed.toml

Project configuration file that tracks installed kits and their artifacts. Structure:

```toml
[kits.<kit-id>]
kit_id = "devrun"
source_type = "bundled"
version = "0.1.0"
artifacts = [
    "skills/devrun-make/SKILL.md",
    "agents/devrun/runner.md",
]
```

### InstalledKit

Data model representing a kit entry in `installed.toml`:

- `kit_id`: Unique identifier for the kit
- `source_type`: Where the kit came from (bundled, git, etc.)
- `version`: Semantic version of the kit
- `artifacts`: List of relative paths to installed artifacts

## Data Models

### InstalledArtifact

Represents an artifact with full metadata:

```python
@dataclass(frozen=True)
class InstalledArtifact:
    artifact_type: ArtifactType      # "skill", "command", "agent", "hook", "doc"
    artifact_name: str               # Display name
    file_path: Path                  # Relative to .claude/
    source: ArtifactSource           # MANAGED or LOCAL
    level: ArtifactLevel             # USER or PROJECT
    kit_id: str | None               # Kit identifier if managed
    kit_version: str | None          # Kit version if managed
    settings_source: str | None      # For hooks: which settings file
```

### ArtifactSource (Enum)

```python
class ArtifactSource(Enum):
    MANAGED = "managed"  # Tracked in installed.toml
    LOCAL = "local"      # Created manually, no kit association
```

### ArtifactLevel (Enum)

```python
class ArtifactLevel(Enum):
    USER = "user"        # Installed in ~/.claude/
    PROJECT = "project"  # Installed in ./.claude/
```

## Common Patterns

### Checking if an artifact is from a kit

```python
if artifact.source == ArtifactSource.MANAGED:
    # This artifact was installed from a kit
    print(f"From kit: {artifact.kit_id} v{artifact.kit_version}")
```

### Filtering artifacts by level

```python
user_artifacts = [a for a in artifacts if a.level == ArtifactLevel.USER]
project_artifacts = [a for a in artifacts if a.level == ArtifactLevel.PROJECT]
```

### Finding all artifacts from a specific kit

```python
kit_artifacts = [a for a in artifacts if a.kit_id == "devrun"]
```

## CLI Commands Reference

### Filtering Options

Most artifact commands support these filters:

- `--user` / `--project` / `--all`: Filter by level (default: all)
- `--type <type>`: Filter by artifact type (skill, command, agent, hook, doc)
- `--managed`: Show only artifacts installed from kits (exclude local)
- `-v` / `--verbose`: Show detailed information

### Examples

```bash
# List all artifacts
erk artifact list

# List only project-level skills
erk artifact list --project --type skill

# List only artifacts from kits (exclude manually created)
erk artifact list --managed

# List managed skills at project level
erk artifact list --managed --type skill --project
```
