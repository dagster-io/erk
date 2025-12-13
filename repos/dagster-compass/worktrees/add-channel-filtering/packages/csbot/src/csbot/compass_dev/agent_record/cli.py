"""CLI commands for agent-record functionality."""

import asyncio
import os
from pathlib import Path

import click

from csbot.agents.messages import AgentMessage
from csbot.compass_dev.agent_record.anthropic.tools.all_tools import get_tools
from csbot.compass_dev.agent_record.factory import get_agent_factory, list_available_agents
from csbot.compass_dev.agent_record.naming import (
    find_naming_violations,
    is_valid_scenario_name,
    suggest_valid_name,
)
from csbot.compass_dev.agent_record.recorder import AsyncAgentRecorder, RecorderConfig
from csbot.compass_dev.agent_record.scenario_loader import load_scenarios


def get_validator_functions(agent_type: str):
    """Get validator functions for the specified agent type."""
    if agent_type == "anthropic":
        from csbot.compass_dev.agent_record.anthropic.validator import (
            list_agent_events,
            list_input_events,
            validate_json_files,
        )
    else:
        raise ValueError(f"Unsupported agent type: {agent_type}")

    return list_agent_events, list_input_events, validate_json_files


def get_recordings_dir(agent_type: str = "anthropic") -> Path:
    """Get the recordings directory path for the specified agent type."""
    return (
        Path(__file__).parent.parent.parent.parent.parent
        / "tests"
        / "agents"
        / "recorded_scenarios"
        / agent_type
        / "recordings"
    )


@click.group(name="agent-record")
def agent_record():
    """Record and validate API responses for multiple agent types.

    Tools for recording real API responses and validating that agents
    correctly process them across different providers (Anthropic, OpenAI, etc.).
    """
    pass


@agent_record.command()
@click.option("--scenario", help="Specific scenario to record")
@click.option("--all", "record_all", is_flag=True, help="Record all scenarios")
@click.option("--agent-type", required=True, help="Agent type to use (anthropic, openai, etc.)")
@click.option("--api-key", help="API key (or set corresponding env var)")
@click.option("--model", help="Model to use (will use agent default if not specified)")
@click.option("--save-as", help="Custom filename for recording")
@click.option("--prompt", help="Custom prompt (for 'custom' scenario)")
@click.option(
    "--tools", help="Tool category for custom scenario (weather, calculator, search, all)"
)
@click.option(
    "--max-tokens", type=int, default=16000, help="Maximum tokens for response generation"
)
@click.option("--list", "list_scenarios", is_flag=True, help="List available scenarios")
def record(
    scenario: str | None,
    record_all: bool,
    agent_type: str,
    api_key: str | None,
    model: str | None,
    save_as: str | None,
    prompt: str | None,
    tools: str | None,
    max_tokens: int,
    list_scenarios: bool,
):
    """Record API responses for scenarios.

    Use --scenario to record a specific scenario, --all to record all scenarios,
    or --list to see available scenarios.
    """

    scenarios = load_scenarios()

    if list_scenarios:
        # Load scenarios for the specified agent type
        scenarios = load_scenarios(agent_type)

        click.echo("Available scenarios:")
        for name, info in scenarios.items():
            click.echo(f"  {name}: {info.get('description', 'No description')}")

        click.echo(f"\nAvailable agent types: {', '.join(list_available_agents())}")

        click.echo("\n💡 Examples:")
        click.echo(
            "  compass-dev agent-record record --agent-type anthropic --scenario simple_text"
        )
        click.echo(
            "  compass-dev agent-record record --agent-type anthropic --scenario weather-tool"
        )
        click.echo(
            "  compass-dev agent-record record --agent-type anthropic --scenario custom --prompt 'Explain quantum physics'"
        )
        click.echo("  compass-dev agent-record record --agent-type anthropic --all")
        return

    # Validate mutually exclusive options
    if record_all and scenario:
        raise click.ClickException("Cannot specify both --all and --scenario")

    if not record_all and not scenario:
        raise click.ClickException("Must specify --scenario, --all, or --list")

    # Validate agent type
    try:
        factory = get_agent_factory(agent_type)
    except ValueError as e:
        raise click.ClickException(str(e))

    # Get API key from option or environment
    if not api_key:
        # Try different environment variables based on agent type
        env_vars = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            # Add more as needed
        }
        env_var = env_vars.get(agent_type, f"{agent_type.upper()}_API_KEY")
        api_key = os.getenv(env_var)
        if not api_key:
            raise click.ClickException(
                f"API key required. Set {env_var} environment variable or use --api-key"
            )

    # Set default model if not specified
    if not model:
        supported_models = factory.get_supported_models()
        if supported_models:
            model = supported_models[0]  # Use first supported model as default
        else:
            raise click.ClickException(f"No default model available for agent type: {agent_type}")

    # Load scenarios for the specified agent type
    scenarios = load_scenarios(agent_type)

    # Create recorder using factory
    recordings_dir = get_recordings_dir(agent_type)
    recorder_config = RecorderConfig(api_key=api_key, output_dir=recordings_dir)
    recorder = factory.create_recorder(recorder_config)

    # Handle recording
    if record_all:
        _record_all_scenarios(recorder, scenarios, model, max_tokens)
    elif scenario == "custom":
        if not prompt:
            raise click.ClickException("Custom scenario requires --prompt")
        _record_custom_scenario(recorder, prompt, model, save_as, tools, max_tokens)
    elif scenario in scenarios:
        _record_scenario(recorder, scenarios, scenario, model, save_as, max_tokens)
    else:
        available = list(scenarios.keys()) + ["custom"]
        raise click.ClickException(
            f"Unknown scenario: {scenario}. Available: {', '.join(available)}"
        )


def _record_scenario(
    recorder: AsyncAgentRecorder,
    scenarios: dict[str, dict],
    scenario: str,
    model: str,
    save_as: str | None,
    max_tokens: int,
):
    """Record a single scenario."""
    click.echo(f"🎬 Recording {scenario} scenario...")

    scenario_info = scenarios[scenario]
    messages = scenario_info["messages"]
    tools = scenario_info.get("tools")

    if not isinstance(messages, list):
        raise TypeError(f"Expected list of messages, got {type(messages)}")

    # Ensure messages are properly typed
    typed_messages: list[AgentMessage] = []
    for msg in messages:
        if isinstance(msg, AgentMessage):
            typed_messages.append(msg)
        else:
            raise TypeError(f"Expected AgentMessage, got {type(msg)}")

    if tools:
        click.echo(f"🔧 Using tools: {len(tools)} tools available")

    system = scenario_info.get("system", "You are a helpful assistant.")
    result = asyncio.run(
        recorder.record_scenario(
            scenario_name=scenario,
            system=system,
            messages=typed_messages,
            model=model,
            tools=tools,
            max_tokens=max_tokens,
            save_as=save_as,
        )
    )
    click.echo(f"✅ Recording saved: {result.get('output_path', 'Unknown path')}")


def _record_custom_scenario(
    recorder: AsyncAgentRecorder,
    prompt: str,
    model: str,
    save_as: str | None,
    tools: str | None,
    max_tokens: int,
):
    """Record a custom scenario with user prompt."""
    click.echo("🎬 Recording custom scenario...")

    from csbot.agents.messages import AgentTextMessage

    messages: list[AgentMessage] = [AgentTextMessage(role="user", content=prompt)]
    scenario_tools = None
    if tools:
        scenario_tools = get_tools(tools)
        click.echo(f"🔧 Using tools: {tools}")

    result = asyncio.run(
        recorder.record_scenario(
            scenario_name="custom",
            system="You are a helpful assistant.",
            messages=messages,
            model=model,
            tools=scenario_tools,
            max_tokens=max_tokens,
            save_as=save_as,
        )
    )
    click.echo(f"✅ Recording saved: {result.get('output_path', 'Unknown path')}")


def _record_all_scenarios(
    recorder: AsyncAgentRecorder, scenarios: dict[str, dict], model: str, max_tokens: int
):
    """Record all available scenarios."""
    click.echo("🎬 Recording all scenarios...")

    for scenario_name in scenarios.keys():
        click.echo(f"  📝 Recording {scenario_name}...")
        try:
            _record_scenario(recorder, scenarios, scenario_name, model, None, max_tokens)
        except Exception as e:
            click.echo(f"❌ Failed to record {scenario_name}: {e}")
            raise click.ClickException(f"Recording failed for {scenario_name}")

    click.echo("🎉 All scenarios recorded successfully!")


@agent_record.command()
@click.argument("recording_name")
@click.option("--agent-type", required=True, help="Agent type to search for recording")
@click.option("--agent-events", is_flag=True, help="Show AgentEvents generated from the recording")
@click.option("--input-events", is_flag=True, help="Show raw input events from the recording")
@click.option(
    "--verbose",
    is_flag=True,
    help="Show detailed information including request context and tool definitions",
)
def inspect(
    recording_name: str, agent_type: str, agent_events: bool, input_events: bool, verbose: bool
):
    """Inspect events from a specific recording.

    RECORDING_NAME: Name of the recording file (with or without .json extension)
    """
    # Validate mutually exclusive options
    if agent_events and input_events:
        raise click.ClickException("Cannot specify both --agent-events and --input-events")

    if not agent_events and not input_events:
        raise click.ClickException("Must specify either --agent-events or --input-events")

    recordings_dir = get_recordings_dir(agent_type)

    # Find the recording file
    if not recording_name.endswith(".json"):
        recording_name += ".json"

    recording_path = None
    for json_file in recordings_dir.rglob(recording_name):
        if not json_file.name.startswith("_"):
            recording_path = json_file
            break

    if not recording_path:
        raise click.ClickException(f"Recording not found: {recording_name}")

    # Get validator functions for the agent type
    try:
        list_agent_events, list_input_events, _ = get_validator_functions(agent_type)
    except ValueError as e:
        raise click.ClickException(str(e))

    # Run the appropriate inspection
    original_cwd = os.getcwd()
    try:
        os.chdir(Path(__file__).parent)
        import asyncio

        if agent_events:
            exit_code = asyncio.run(list_agent_events(recording_path, verbose))
        else:  # input_events
            exit_code = asyncio.run(list_input_events(recording_path, verbose))

        if exit_code != 0:
            raise click.ClickException("Inspection failed")
    finally:
        os.chdir(original_cwd)


def _validate_scenarios_yaml(agent_type: str, verbose: bool) -> bool:
    """Validate scenarios YAML file can be parsed and references valid tools."""
    import yaml

    from csbot.compass_dev.agent_record.anthropic.tools.all_tools import TOOL_COLLECTIONS

    # Map agent types to directory names to avoid import conflicts
    agent_dir_map = {"anthropic": "anthropic_recordings", "openai": "openai"}
    agent_dir = agent_dir_map.get(agent_type, agent_type)

    scenarios_file = (
        Path(__file__).parent.parent.parent.parent.parent
        / "tests"
        / "agents"
        / "recorded_scenarios"
        / agent_dir
        / "scenarios.yaml"
    )

    if not scenarios_file.exists():
        click.echo(f"❌ Scenarios file not found: {scenarios_file}")
        return False

    try:
        # Test YAML parsing
        with open(scenarios_file, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        if verbose:
            click.echo(f"📁 Loaded scenarios from: {scenarios_file}")

        if "scenarios" not in config:
            click.echo("❌ YAML missing 'scenarios' key")
            return False

        valid_tool_categories = set(TOOL_COLLECTIONS.keys())
        if verbose:
            click.echo(f"🔧 Valid tool categories: {sorted(valid_tool_categories)}")

        scenarios = config["scenarios"]
        if verbose:
            click.echo(f"📋 Found {len(scenarios)} scenarios")

        # Validate each scenario
        for scenario_name, scenario_config in scenarios.items():
            if verbose:
                click.echo(f"  🔍 Validating scenario: {scenario_name}")

            # Validate naming convention (no underscores, allow hyphens)
            if not is_valid_scenario_name(scenario_name):
                suggested = suggest_valid_name(scenario_name)
                click.echo(
                    f"❌ Scenario '{scenario_name}' uses invalid naming. Use lowercase letters, numbers, and hyphens only (e.g., '{suggested}')"
                )
                return False

            # Check required fields
            if "messages" not in scenario_config:
                click.echo(f"❌ Scenario '{scenario_name}' missing 'messages' field")
                return False

            if "description" not in scenario_config:
                click.echo(f"❌ Scenario '{scenario_name}' missing 'description' field")
                return False

            # Validate messages structure
            messages = scenario_config["messages"]
            if not isinstance(messages, list):
                click.echo(f"❌ Scenario '{scenario_name}' messages must be a list")
                return False

            for i, message in enumerate(messages):
                if not isinstance(message, dict):
                    click.echo(f"❌ Scenario '{scenario_name}' message {i} must be a dict")
                    return False

                if "role" not in message or "content" not in message:
                    click.echo(
                        f"❌ Scenario '{scenario_name}' message {i} missing 'role' or 'content'"
                    )
                    return False

            # Validate tools if present
            if "tools" in scenario_config:
                tools = scenario_config["tools"]
                if not isinstance(tools, list):
                    click.echo(f"❌ Scenario '{scenario_name}' tools must be a list")
                    return False

                for tool_category in tools:
                    if tool_category not in valid_tool_categories:
                        click.echo(
                            f"❌ Scenario '{scenario_name}' references invalid tool category: '{tool_category}'"
                        )
                        click.echo(f"   Valid categories: {sorted(valid_tool_categories)}")
                        return False

                if verbose:
                    click.echo(f"    🔧 Tools: {tools}")

        # Test that we can load scenarios using the loader
        try:
            from csbot.compass_dev.agent_record.scenario_loader import load_scenarios

            loaded_scenarios = load_scenarios()

            if len(loaded_scenarios) != len(scenarios):
                click.echo(
                    f"❌ Loader returned {len(loaded_scenarios)} scenarios, expected {len(scenarios)}"
                )
                return False

            if verbose:
                click.echo(f"✅ Successfully loaded {len(loaded_scenarios)} scenarios via loader")

        except Exception as e:
            click.echo(f"❌ Failed to load scenarios via loader: {e}")
            return False

        return True

    except yaml.YAMLError as e:
        click.echo(f"❌ YAML parsing error: {e}")
        return False
    except Exception as e:
        click.echo(f"❌ Validation error: {e}")
        return False


@agent_record.command()
@click.option("--agent-type", required=True, help="Agent type to validate")
@click.option("--verbose", is_flag=True, help="Verbose output")
def check(agent_type: str, verbose: bool):
    """Check that all JSON files are parseable and scenarios YAML is valid."""
    recordings_dir = get_recordings_dir(agent_type)

    # First, validate scenarios YAML
    click.echo("🔍 Validating scenarios.yaml...")
    yaml_validation_passed = _validate_scenarios_yaml(agent_type, verbose)

    if not yaml_validation_passed:
        raise click.ClickException("Scenarios YAML validation failed")

    click.echo("✅ Scenarios YAML validation passed")

    # Then validate JSON recordings
    click.echo("🔍 Validating JSON recordings...")

    # Get validator functions for the agent type
    try:
        _, _, validate_json_files = get_validator_functions(agent_type)
    except ValueError as e:
        raise click.ClickException(str(e))

    original_cwd = os.getcwd()
    try:
        os.chdir(Path(__file__).parent)
        import asyncio

        exit_code = asyncio.run(validate_json_files(recordings_dir, verbose))

        if exit_code != 0:
            raise click.ClickException("JSON validation failed")

        click.echo("✅ All validations passed")
    finally:
        os.chdir(original_cwd)


@agent_record.command(name="list")
@click.option("--agent-type", required=True, help="Agent type to list recordings for")
def list_recordings(agent_type: str):
    """List available recordings."""
    recordings_dir = get_recordings_dir(agent_type)

    if not recordings_dir.exists():
        click.echo("❌ No recordings directory found")
        return

    click.echo("📁 Available recordings:")

    # Collect all recordings from all subdirectories
    all_recordings = []
    for json_file in recordings_dir.rglob("*.json"):
        if not json_file.name.startswith("_"):  # Skip private files
            # Remove .json extension for display
            name = json_file.name.removesuffix(".json")
            all_recordings.append(name)

    # Display as flat sorted list
    for recording in sorted(all_recordings):
        click.echo(f"  {recording}")

    click.echo(f"\n📊 Total recordings: {len(all_recordings)}")


@agent_record.command()
@click.option("--agent-type", required=True, help="Agent type to fix naming for")
@click.option(
    "--dry-run", is_flag=True, help="Show what would be renamed without actually doing it"
)
def fix_naming(agent_type: str, dry_run: bool):
    """Fix naming convention violations by renaming files and updating scenarios."""
    import json

    recordings_dir = get_recordings_dir(agent_type)

    if not recordings_dir.exists():
        click.echo("❌ No recordings directory found")
        return

    # Find files with naming violations
    violations = find_naming_violations(recordings_dir)

    if not violations:
        click.echo("✅ No naming convention violations found")
        return

    click.echo(f"🔧 Found {len(violations)} files to rename:")

    for file_path, old_name in violations:
        new_name = suggest_valid_name(old_name)
        new_path = file_path.parent / f"{new_name}.json"

        if dry_run:
            click.echo(f"  {old_name} → {new_name}")
        else:
            click.echo(f"  Renaming {old_name} → {new_name}")

            # Update scenario name in JSON metadata
            try:
                with open(file_path, encoding="utf-8") as f:
                    data = json.load(f)

                if "metadata" in data and "scenario" in data["metadata"]:
                    data["metadata"]["scenario"] = new_name

                with open(new_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                # Remove old file
                file_path.unlink()

            except Exception as e:
                click.echo(f"    ❌ Failed to update {old_name}: {e}")
                continue

    if dry_run:
        click.echo("\n💡 Run without --dry-run to perform the renames")
    else:
        click.echo(f"\n✅ Renamed {len(violations)} files")


@agent_record.command(name="agents")
def list_agents():
    """List available agent types."""
    click.echo("🤖 Available agent types:")

    for agent_type in list_available_agents():
        try:
            factory = get_agent_factory(agent_type)
            models = factory.get_supported_models()
            click.echo(f"  {agent_type}:")
            if models:
                click.echo(f"    Models: {', '.join(models[:3])}")
                if len(models) > 3:
                    click.echo(f"    (+{len(models) - 3} more)")
            else:
                click.echo("    No models configured")
        except Exception as e:
            click.echo(f"  {agent_type}: Error - {e}")

    click.echo(f"\n📊 Total agent types: {len(list_available_agents())}")
