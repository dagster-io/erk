from pathlib import Path

import pytest
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

from tests.e2e.helpers import assert_file_contains, collect_response


@pytest.mark.e2e
@pytest.mark.timeout(300)
async def test_hello_world_plan_and_implement(temp_python_repo: Path) -> None:
    """Test the full planning workflow: plan, approve, implement, verify."""
    options = ClaudeAgentOptions(
        cwd=str(temp_python_repo),
        permission_mode="bypassPermissions",
        max_turns=30,
        system_prompt={"type": "preset", "preset": "claude_code"},
        setting_sources=[],
    )

    async with ClaudeSDKClient(options) as client:
        # Turn 1: Ask Claude to create a plan
        await client.query(
            "I want to add a print('Hello, world!') statement to main.py. "
            "First, read the file and tell me your plan for where to add it. "
            "Do NOT make any changes yet - just describe your plan."
        )
        plan_text, _ = await collect_response(client)

        # Verify Claude produced a plan mentioning the file
        plan_lower = plan_text.lower()
        assert "main.py" in plan_lower or "hello" in plan_lower, (
            f"Expected plan to mention main.py or hello, got: {plan_text[:500]}"
        )

        # Turn 2: Approve and implement
        await client.query(
            "That plan looks good. Go ahead and implement it now - "
            "add print('Hello, world!') to main.py."
        )
        _, _ = await collect_response(client)

        # Verify the file was modified
        assert_file_contains(temp_python_repo / "main.py", "Hello, world!")
