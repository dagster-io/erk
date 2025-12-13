# Why Compass programs to AsyncAgent, an Anthropic-centric API?

## Context

Compass builds fine-grained interactive experiences with LLMs, delivered primarily through Slack.
Our application requires:

- **True streaming** of both text and tool calls
- **Live reconciliation** of in-progress agent state into Slack Block Kit
- **Early, partial feedback** on what the model is doing
- **Tight latency/throughput control** for production-scale usage

Because of this, we program directly to Anthropic's event model as our **primary API**.

---

## Anthropic capabilities we depend on

1. **Structured content blocks**
   - Events have explicit `start → delta → stop` lifecycle.
   - Supports interleaving of text and tool calls in a single turn.
   - Enables deterministic reconciliation in Slack.

2. **Partial tool-input streaming**
   - Tool arguments (often long SQL or JSON) arrive incrementally as `partial_json` deltas.
   - UI can display a "building query…" block and update live as clauses appear.
   - Reduces perceived latency and improves trust/debuggability.

3. **Stop reasons and usage reporting during stream**
   - Token usage and stop conditions are surfaced mid-stream, not only at the end.
   - Allows proactive error handling (e.g., "Token Limit Exceeded") and real-time cost reporting.

4. **Cache-control hints**
   - Anthropic supports marking blocks as ephemeral or cacheable.
   - Lets us save tokens and reduce latency on repeated system/context prompts.

5. **Multiple tool calls per turn**
   - Models can emit several `tool_use` blocks before ending a turn.
   - Our loop handles this seamlessly, yielding rich multi-tool workflows.

---

## Supported Providers

Compass currently supports:

- **Anthropic** (primary): Full-featured support using Anthropic's native API
- **AWS Bedrock**: Anthropic models via AWS infrastructure

Both providers use Anthropic's Claude models and support the full feature set including streaming, tool calls, and cache control.
