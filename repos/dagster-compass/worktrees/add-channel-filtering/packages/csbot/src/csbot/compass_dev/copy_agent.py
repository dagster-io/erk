"""Agent management commands."""

import shutil
from pathlib import Path

import click


def get_agent_info(agent_file: Path) -> dict[str, str]:
    """Extract agent info from frontmatter."""
    info = {"name": agent_file.stem, "description": ""}

    # Check if file exists and is readable before attempting to parse
    if not agent_file.exists() or not agent_file.is_file():
        return info

    # Check if file is readable by checking permissions
    try:
        agent_file.stat()
    except (OSError, PermissionError):
        return info

    with open(agent_file) as f:
        content = f.read()
        if content.startswith("---\n"):
            lines = content.split("\n")
            for line in lines[1:20]:  # Look in first 20 lines of frontmatter
                if line == "---":
                    break
                if line.startswith("name:"):
                    info["name"] = line.split(":", 1)[1].strip()
                elif line.startswith("description:"):
                    info["description"] = line.split(":", 1)[1].strip()

    return info


def _validate_repo_path(dagster_repo_path: str) -> Path:
    """Validate and resolve repository path to prevent path traversal attacks."""
    dagster_repo = Path(dagster_repo_path).resolve()

    # Prevent path traversal by ensuring the resolved path is within expected bounds
    # Convert to string for safer comparison
    resolved_str = str(dagster_repo)

    # Block obvious path traversal attempts
    if (
        ".." in dagster_repo_path
        or resolved_str.startswith("/etc/")
        or resolved_str.startswith("/usr/")
        or resolved_str.startswith("/var/")
        or resolved_str.startswith("/root/")
    ):
        raise ValueError(f"Invalid repository path: {dagster_repo_path}")

    return dagster_repo


def copy_from_dagster_impl(agent_name: str, dagster_repo_path: str) -> None:
    """Copy an agent from the main dagster repo to compass."""
    dagster_repo = _validate_repo_path(dagster_repo_path)

    if not dagster_repo.exists():
        raise FileNotFoundError(f"Dagster repository not found at: {dagster_repo}")

    dagster_agents_dir = dagster_repo / ".claude" / "agents"
    if not dagster_agents_dir.exists():
        raise FileNotFoundError(f"Dagster agents directory not found at: {dagster_agents_dir}")

    # Find the agent file
    agent_file = dagster_agents_dir / f"{agent_name}.md"
    if not agent_file.exists():
        # List available agents for helpful error message
        available_agents = [f.stem for f in dagster_agents_dir.glob("*.md")]
        available_str = ", ".join(available_agents) if available_agents else "none"
        raise FileNotFoundError(
            f"Agent '{agent_name}' not found in dagster repo. Available: {available_str}"
        )

    # Create destination directory if it doesn't exist
    compass_agents_dir = Path.cwd() / ".claude" / "agents"
    compass_agents_dir.mkdir(parents=True, exist_ok=True)

    # Copy the agent file
    dest_file = compass_agents_dir / f"{agent_name}.md"
    shutil.copy2(agent_file, dest_file)

    # Show success message with info
    info = get_agent_info(dest_file)
    click.echo(f"✅ Copied '{info['name']}' from dagster to compass")
    if info["description"]:
        desc = info["description"]
        if len(desc) > 100:
            desc = desc[:100] + "..."
        click.echo(f"   Description: {desc}")


def copy_to_dagster_impl(agent_name: str, dagster_repo_path: str) -> None:
    """Copy an agent from compass to the main dagster repo."""
    dagster_repo = _validate_repo_path(dagster_repo_path)

    if not dagster_repo.exists():
        raise FileNotFoundError(f"Dagster repository not found at: {dagster_repo}")

    # Find the agent file in compass
    compass_agents_dir = Path.cwd() / ".claude" / "agents"
    if not compass_agents_dir.exists():
        raise FileNotFoundError("No .claude/agents directory found in compass")

    agent_file = compass_agents_dir / f"{agent_name}.md"
    if not agent_file.exists():
        # List available agents for helpful error message
        available_agents = [f.stem for f in compass_agents_dir.glob("*.md")]
        available_str = ", ".join(available_agents) if available_agents else "none"
        raise FileNotFoundError(
            f"Agent '{agent_name}' not found in compass. Available: {available_str}"
        )

    # Create destination directory if it doesn't exist
    dagster_agents_dir = dagster_repo / ".claude" / "agents"
    dagster_agents_dir.mkdir(parents=True, exist_ok=True)

    # Copy the agent file
    dest_file = dagster_agents_dir / f"{agent_name}.md"
    shutil.copy2(agent_file, dest_file)

    # Show success message with info
    info = get_agent_info(dest_file)
    click.echo(f"✅ Copied '{info['name']}' from compass to dagster")
    if info["description"]:
        desc = info["description"]
        if len(desc) > 100:
            desc = desc[:100] + "..."
        click.echo(f"   Description: {desc}")


def list_agents_impl(dagster_repo_path: str) -> None:
    """List all agents in both compass and dagster repos."""
    dagster_repo = _validate_repo_path(dagster_repo_path)
    compass_agents_dir = Path.cwd() / ".claude" / "agents"
    dagster_agents_dir = dagster_repo / ".claude" / "agents"

    # Get compass agents
    compass_agents = {}
    if compass_agents_dir.exists():
        for agent_file in compass_agents_dir.glob("*.md"):
            info = get_agent_info(agent_file)
            compass_agents[agent_file.stem] = info

    # Get dagster agents
    dagster_agents = {}
    if dagster_agents_dir.exists():
        for agent_file in dagster_agents_dir.glob("*.md"):
            info = get_agent_info(agent_file)
            dagster_agents[agent_file.stem] = info

    # Display results
    click.echo("📋 Agent inventory:")
    click.echo()

    # Show compass agents
    click.echo("🧭 Compass agents:")
    if compass_agents:
        for name, info in sorted(compass_agents.items()):
            click.echo(f"  • {name}")
            if info["description"]:
                desc = info["description"]
                if len(desc) > 80:
                    desc = desc[:80] + "..."
                click.echo(f"    {desc}")
    else:
        click.echo("  (no agents found)")

    click.echo()

    # Show dagster agents
    click.echo("⚙️  Dagster agents:")
    if dagster_agents:
        for name, info in sorted(dagster_agents.items()):
            # Mark if also in compass
            marker = "  • "
            if name in compass_agents:
                marker = "  ✓ "  # Already in compass
            click.echo(f"{marker}{name}")
            if info["description"]:
                desc = info["description"]
                if len(desc) > 80:
                    desc = desc[:80] + "..."
                click.echo(f"    {desc}")
    else:
        click.echo("  (no agents found)")

    click.echo()
    click.echo("Legend: ✓ = also in compass")


@click.group()
def copy_agent():
    """Manage agents between compass and dagster repos."""
    pass


@copy_agent.command("from-dagster")
@click.argument("agent_name")
@click.option(
    "--dagster-repo",
    default="../dagster",
    help="Path to the main dagster repository (default: ../dagster)",
)
def copy_from_dagster(agent_name: str, dagster_repo: str) -> None:
    """Copy an agent FROM the main dagster repo TO compass.

    AGENT_NAME: Name of the agent to copy (e.g., 'agent-coach')
    """
    try:
        copy_from_dagster_impl(agent_name, dagster_repo)
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@copy_agent.command("to-dagster")
@click.argument("agent_name")
@click.option(
    "--dagster-repo",
    default="../dagster",
    help="Path to the main dagster repository (default: ../dagster)",
)
def copy_to_dagster(agent_name: str, dagster_repo: str) -> None:
    """Copy an agent FROM compass TO the main dagster repo.

    AGENT_NAME: Name of the agent to copy
    """
    try:
        copy_to_dagster_impl(agent_name, dagster_repo)
    except FileNotFoundError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        raise click.Abort()


@copy_agent.command("ls")
@click.option(
    "--dagster-repo",
    default="../dagster",
    help="Path to the main dagster repository (default: ../dagster)",
)
def list_agents(dagster_repo: str) -> None:
    """List all agents in both compass and dagster repos."""
    try:
        list_agents_impl(dagster_repo)
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
