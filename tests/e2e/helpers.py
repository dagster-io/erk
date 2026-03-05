from pathlib import Path

from claude_agent_sdk import AssistantMessage, ClaudeSDKClient, TextBlock


async def collect_response(client: ClaudeSDKClient) -> tuple[str, list[object]]:
    """Collect all messages from a response, return (text, all_messages)."""
    text_parts: list[str] = []
    messages: list[object] = []
    async for message in client.receive_response():
        messages.append(message)
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    text_parts.append(block.text)
    return "\n".join(text_parts), messages


def assert_file_contains(path: Path, substring: str) -> None:
    """Assert a file exists and contains the given substring."""
    assert path.exists(), f"File {path} does not exist"
    content = path.read_text()
    assert substring in content, f"'{substring}' not found in {path}"
