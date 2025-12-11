"""Scenario loader for agent-record functionality."""

from pathlib import Path
from typing import Any

import yaml

from csbot.agents.messages import AgentTextMessage

from .anthropic.tools.all_tools import get_tools


def load_scenarios(agent_type: str = "anthropic") -> dict[str, dict[str, Any]]:
    """Load scenarios from YAML configuration file for the specified agent type."""
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

    with open(scenarios_file, encoding="utf-8") as f:
        config = yaml.safe_load(f)

    scenarios = {}
    for name, scenario_config in config["scenarios"].items():
        scenario = {
            "description": scenario_config["description"],
            "messages": [
                AgentTextMessage(role=msg["role"], content=msg["content"])
                for msg in scenario_config["messages"]
            ],
        }

        # Add system prompt if specified
        if "system" in scenario_config:
            scenario["system"] = scenario_config["system"]
        else:
            scenario["system"] = "You are a helpful assistant."

        # Add tools if specified
        if "tools" in scenario_config:
            tools_dict = {}
            for tool_category in scenario_config["tools"]:
                # Import tools based on agent type
                if agent_type in ["anthropic", "openai"]:
                    category_tools = get_tools(tool_category)
                    tools_dict.update(category_tools)
                else:
                    # For other agent types, we'll need to implement their tool systems
                    # For now, just skip tools for unknown agent types
                    pass
            scenario["tools"] = tools_dict

        scenarios[name] = scenario

    return scenarios
