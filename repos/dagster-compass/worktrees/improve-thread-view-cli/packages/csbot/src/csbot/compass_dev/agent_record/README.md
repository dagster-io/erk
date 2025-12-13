# agent-record

A testing and validation framework for the AnthropicAgent system, designed to record and validate Anthropic API responses and their conversion to Agent events.

## Overview

agent-record provides comprehensive tools for:

- **Recording real Anthropic API responses** from various test scenarios
- **Validating event stream mappings** between raw Anthropic events and Agent events
- **Inspecting recorded scenarios** to understand event flow and debug issues
- **Managing test scenarios** through YAML configuration

## Architecture

### Core Components

- **ResponseRecorder** (`recorder.py`): Records actual Anthropic API streaming responses using RecordingAnthropicAgent
- **ResponseValidator** (`validator.py`): Validates recordings and provides inspection tools for events
- **ScenarioLoader** (`scenario_loader.py`): Loads test scenarios from YAML configuration
- **CLI** (`cli.py`): Command-line interface for recording, inspecting, and validating

### Directory Structure

```
agent_record/
├── cli.py                    # CLI command definitions
├── recorder.py               # API response recording
├── validator.py              # Event validation and inspection
├── scenario_loader.py        # Scenario configuration loading
├── utils.py                  # Shared utilities
└── tools/                    # Mock tool implementations
    ├── all_tools.py          # Tool collection registry
    ├── calculator_tool.py    # Calculator tool mock
    ├── search_tool.py        # Search tool mock
    └── weather_tool.py       # Weather tool mock
```

## Commands

### `record` - Record API Responses

Records real Anthropic API responses for testing scenarios using AnthropicAgent.

```bash
# List available scenarios
compass-dev agent-record record --list

# Record a specific scenario
compass-dev agent-record record --scenario simple_text

# Record with tools
compass-dev agent-record record --scenario weather-tool

# Custom recording with prompt
compass-dev agent-record record --scenario custom \
  --prompt "Explain quantum physics" \
  --tools search

# Record all scenarios
compass-dev agent-record record --all
```

**Options:**

- `--scenario`: Record a specific scenario
- `--all`: Record all configured scenarios
- `--api-key`: Anthropic API key (or use ANTHROPIC_API_KEY env var)
- `--model`: Model to use (default: claude-sonnet-4-20250514)
- `--max-tokens`: Maximum tokens for response generation (default: 50000)
- `--save-as`: Custom filename for recording
- `--prompt`: Custom prompt for 'custom' scenario
- `--tools`: Tool category for custom scenario (weather, calculator, search, all)
- `--list`: List available scenarios

### `inspect` - Inspect Recorded Events

Examines events from recorded scenarios to understand the event flow.

```bash
# Inspect raw Anthropic events
compass-dev agent-record inspect simple_text --input-events

# Inspect generated Agent events
compass-dev agent-record inspect weather-tool --agent-events

# Verbose inspection with full context
compass-dev agent-record inspect search-tool --agent-events --verbose
```

**Options:**

- `--agent-events`: Show Agent events generated from the recording
- `--input-events`: Show raw Anthropic input events
- `--verbose`: Show detailed information including request context

### `check` - Validate Recordings

Validates that all JSON recordings are parseable and scenarios YAML is valid.

```bash
# Basic validation
compass-dev agent-record check

# Verbose validation
compass-dev agent-record check --verbose
```

### `list` - List Available Recordings

Lists all available recorded scenarios.

```bash
compass-dev agent-record list
```

## Recording Structure

Recordings are stored as JSON files with the following structure:

```json
{
  "metadata": {
    "recorded_at": "2024-01-01T12:00:00Z",
    "scenario": "simple_text",
    "model": "claude-sonnet-4-20250514",
    "anthropic_client_version": "0.25.1",
    "recorder_version": "1.0",
    "duration_seconds": 1.23,
    "raw_event_count": 42,
    "agent_block_event_count": 15,
    "agent_type": "AnthropicAgent"
  },
  "request_params": {
    "messages": [
      {"role": "user", "content": "Hello"}
    ],
    "tools": ["weather", "calculator"],
    "model": "claude-sonnet-4-20250514",
    "max_tokens": 50000,
    "temperature": 0.7
  },
  "raw_anthropic_events": [
    {
      "type": "message_start",
      "timestamp": "2024-01-01T12:00:00Z",
      "message": {...}
    }
  ],
  "agent_block_events": [
    {
      "event": {
        "type": "start",
        "index": 0,
        "content_block": {...}
      },
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "agent_messages": [
    {
      "role": "assistant",
      "content": "Generated response content"
    }
  ]
}
```

## Recording Organization

Recordings are automatically organized in the test directory:

```
tests/agents/anthropic/recorded_scenarios/recordings/
├── simple_text.json
├── weather-tool.json
├── calculator-tool.json
└── search-tool.json
```

## Scenario Configuration

Scenarios are defined in `tests/agents/anthropic/recorded_scenarios/scenarios.yaml`:

```yaml
scenarios:
  simple_text:
    description: "Basic text response"
    messages:
      - role: user
        content: "Say hello"

  weather-tool:
    description: "Tool calling example"
    messages:
      - role: user
        content: "What's the weather in Paris?"
    tools: ["weather"]

  calculator-tool:
    description: "Calculator tool usage"
    messages:
      - role: user
        content: "Calculate 15 * 7 + 23 - 8"
    tools: ["calculator"]
```

## Event Types

### Anthropic Events

Raw events from the Anthropic API:

- `message_start`: Beginning of response
- `content_block_start`: Start of content block (text or tool use)
- `content_block_delta`: Incremental content updates
- `content_block_stop`: End of content block
- `message_delta`: Message metadata updates
- `message_stop`: End of response

### Agent Events

Events processed by the AnthropicAgent system:

- `AgentStartEvent`: Content block start
- `AgentDeltaEvent`: Incremental content updates (text or tool JSON)
- `AgentStopEvent`: Content block completion

## Use Cases

### 1. Testing Agent Processing

Validate that the AnthropicAgent correctly converts raw Anthropic streaming events to the Agent event protocol.

### 2. Regression Testing

Record API responses from new model versions and validate backward compatibility.

### 3. Debugging

Inspect the exact sequence of events in problematic scenarios to identify issues.

### 4. Documentation

Generate examples of event flows for different interaction patterns.

### 5. Performance Analysis

Measure streaming latency and event processing times.

## Development Workflow

### Adding a New Scenario

1. Add scenario definition to `tests/agents/anthropic/recorded_scenarios/scenarios.yaml`:

```yaml
scenarios:
  my_scenario:
    description: "My test scenario"
    messages:
      - role: user
        content: "Test prompt"
    tools: ["calculator"] # Optional
```

2. Record the scenario:

```bash
compass-dev agent-record record --scenario my_scenario
```

3. Inspect the recording:

```bash
compass-dev agent-record inspect my_scenario --agent-events
```

### Creating Custom Tools

1. Implement tool in `tools/` directory following existing patterns
2. Register in `tools/all_tools.py` TOOL_COLLECTIONS
3. Test with custom scenarios using `--tools` parameter

## Key Features

### Scenario Management

- Predefined scenarios for common patterns
- Custom scenarios with arbitrary prompts
- Tool integration support
- Comprehensive scenario validation

### Event Validation

- JSON schema validation for recordings
- Event sequence verification
- Tool call/result tracking
- Agent event generation validation

### Rich Inspection

- Formatted event display with detailed breakdowns
- Automatic text truncation for readability
- Verbose mode for full context
- Request parameter inspection

### Batch Operations

- Record all scenarios at once
- Validate all recordings together
- Regression testing support

## Requirements

- Python 3.13+
- Anthropic API key (for recording)
- Dependencies from pyproject.toml

## Environment Variables

- `ANTHROPIC_API_KEY`: API key for recording (not needed for inspection/validation)

## Testing

The agent-record framework is used extensively in the test suite for validating AnthropicAgent behavior with real API responses.

## Troubleshooting

### Recording Fails

- Check API key is set correctly
- Verify network connectivity
- Ensure sufficient API quota
- Check model availability

### Validation Errors

- Check recording file integrity with `compass-dev agent-record check`
- Verify scenario configuration syntax
- Review event sequence logic

### Missing Events

- Enable verbose mode for detailed output
- Check for tool registration issues
- Verify scenario YAML syntax
