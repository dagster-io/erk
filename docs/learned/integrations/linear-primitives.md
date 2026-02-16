---
title: Linear Agent-Native Primitives
description: Linear's agent-native primitives for AI-assisted development
read_when:
  - Considering Linear as an alternative to GitHub Issues
  - Building a Linear gateway for erk
  - Understanding how other tools (Cursor, Devin) integrate with Linear
last_audited: "2026-02-16 14:20 PT"
audit_result: clean
---

# Linear Agent-Native Primitives

Linear has invested heavily in agent-first features since May 2025. This document captures the primitives that are relevant to erk's current and planned capabilities.

## Agent Identity Model

Linear treats agents as **first-class workspace users**, not just API consumers.

### OAuth Scopes

Two opt-in scopes control agent visibility:

| Scope             | Effect                                                            |
| ----------------- | ----------------------------------------------------------------- |
| `app:assignable`  | Agent appears in assignee dropdown, can receive issue assignments |
| `app:mentionable` | Agent can be @mentioned in comments and documents                 |

Without these scopes, your OAuth app functions as a normal API client. With them, your app becomes a visible agent in the workspace.

### Agent vs Human Distinction

Linear maintains a clear separation:

- Issues are **assigned to humans**, **delegated to agents**
- When an agent is delegated an issue, the human remains the primary assignee
- Agent profiles are marked as "app users" in the UI
- Agents can create comments, collaborate on documents, and update issues

This model ensures accountability stays with humans while agents do work.

## AgentSession

The `AgentSession` entity tracks the lifecycle of an agent working on an issue.

### Session States

| State           | Meaning                                                      |
| --------------- | ------------------------------------------------------------ |
| `pending`       | Session created, agent hasn't responded yet                  |
| `active`        | Agent is actively working                                    |
| `awaitingInput` | Agent needs human input to proceed                           |
| `error`         | Something went wrong                                         |
| `complete`      | Work finished successfully                                   |
| `stale`         | Agent became unresponsive (didn't respond within 10 seconds) |

### Session Creation

Sessions are created automatically when:

- Agent is **assigned** an issue
- Agent is **@mentioned** in a comment or document
- Agent is **mentioned in a thread**

Or proactively via GraphQL mutations: `agentSessionCreateOnIssue` (linked to an issue) or `agentSessionCreateOnComment` (linked to a comment thread).

### Key Session Fields

The `AgentSession` GraphQL type includes: `id`, `status`, relationships to `appUser` (the agent), `creator` (human who triggered), `issue`, and `comment`. It also carries `promptContext` (pre-formatted context), `plan` (execution strategy as JSON), `summary`, lifecycle timestamps (`startedAt`/`endedAt`), `externalUrls` (links to PRs), and connections to `activities` and `pullRequests`. See the [Linear GraphQL Schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql) for the full type definition.

### State Management

Linear manages session state automatically based on emitted activities. You don't need to manually update status -- it transitions based on what activities you emit.

## AgentActivity

Agents emit semantic activities to communicate progress. Linear renders these in the UI automatically.

### Activity Types

| Type          | Purpose                   | Content Fields                  |
| ------------- | ------------------------- | ------------------------------- |
| `thought`     | Agent reasoning, planning | `body` (markdown)               |
| `action`      | Tool calls, file edits    | `action`, `parameter`, `result` |
| `elicitation` | Request for human input   | `body` (markdown question)      |
| `response`    | Final output, completion  | `body` (markdown)               |
| `error`       | Failure reporting         | `body` (error message)          |
| `prompt`      | User message to agent     | `body` (markdown)               |

The `AgentActivity` type carries a `content` union (typed per activity type above), an `ephemeral` flag, an optional `signal` modifier, and a link to the parent `AgentSession`. For `action` type content, fields are `action` (e.g., "read_file"), `parameter` (e.g., file path), and optional `result` (markdown).

### Activity Signals

The `signal` field modifies how an activity is interpreted:

| Signal     | Meaning                                 |
| ---------- | --------------------------------------- |
| `auth`     | Agent needs authentication              |
| `continue` | Agent will continue working             |
| `select`   | Agent needs user to select from options |
| `stop`     | Agent is stopping execution             |

### Ephemeral Activities

Set `ephemeral: true` for transient status updates (like "Currently reading file X..."). These disappear when the next activity is emitted, keeping the activity stream clean.

## Guidance System

Linear provides cascading configuration for agent behavior.

### Guidance Hierarchy

```
Workspace guidance (lowest precedence)
    -> Parent team guidance
        -> Current team guidance (highest precedence)
```

The nearest team-specific guidance takes precedence. This allows organization-wide defaults with team-level overrides.

### Guidance in Webhooks

When an `AgentSessionEvent` webhook fires, it includes a `guidance` array of `GuidanceRuleWebhookPayload` entries, each containing a `body` (markdown guidance content) and an `origin` (organization or team). This is like **system prompts managed in Linear**, per-team. Agents receive behavior instructions without needing them hardcoded.

## promptContext

Linear pre-formats context for agents in the `promptContext` field on `AgentSessionEvent` webhooks (for `created` events). It contains the issue title, description, properties, relevant comments, cascading guidance from team/workspace, and thread context if applicable.

Agents receive **ready-to-use context**, not raw data to parse. This eliminates the need for agents to make multiple API calls to understand what they're working on.

## Webhook Events

### AgentSessionEvent

Sent when agent sessions are created or updated. The payload includes `action` ("created" or "updated"), the `agentSession`, the triggering `agentActivity` (if any), OAuth/org identifiers, and -- on `created` events only -- `promptContext`, `guidance`, and `previousComments`. See the [Linear GraphQL Schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql) for the full `AgentSessionEventWebhookPayload` type.

### Timing Requirements

- Must return webhook response within **5 seconds**
- Must emit activity or update external URL within **10 seconds** (or session marked `stale`)

## MCP Server

Linear provides an official MCP server for AI model integration.

### Configuration

```json
{
  "mcpServers": {
    "linear": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.linear.app/mcp"]
    }
  }
}
```

### Capabilities

21 tools for issue/project management: create/update issues, query with filters, manage projects and teams, add comments, update properties. This enables Claude Code to interact with Linear directly without going through erk CLI.

## Existing Agent Integrations

Linear has built integrations with major AI coding tools:

| Agent              | Capabilities                                           |
| ------------------ | ------------------------------------------------------ |
| **Cursor**         | Assign issues, work on code, post PRs, update progress |
| **GitHub Copilot** | Assign issues to Copilot coding agent                  |
| **Factory**        | Spin up remote workspaces for agents                   |
| **Devin**          | Autonomous AI software engineering                     |
| **Codegen**        | Issue-to-PR automation                                 |

### Common Pattern

All integrations follow:

1. Agent is assigned/delegated issue
2. Agent creates AgentSession
3. Agent emits activities as it works
4. Agent links PR via externalUrls
5. Agent completes session with summary

## GraphQL API Reference

The three key mutations for agent integration are:

- **`agentSessionCreateOnIssue`** -- Creates an `AgentSession` linked to an issue. Takes `issueId` and optional `externalUrls`. Returns the session `id`, `status`, and `startedAt`.
- **`agentActivityCreate`** -- Emits an activity. Takes `agentSessionId`, `content` (typed per activity type), optional `ephemeral` flag, and optional `signal` modifier.
- **`agentSessionUpdate`** -- Updates a session with `summary`, `externalUrls`, or other fields. Linear automatically transitions status based on activities.

For full mutation signatures and input types, see the [Linear GraphQL Schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql).

## Sources

- [Linear for Agents](https://linear.app/agents)
- [Agent Interaction Guidelines](https://linear.app/developers/aig)
- [Agent Interaction SDK blog](https://linear.app/now/our-approach-to-building-the-agent-interaction-sdk)
- [How Cursor integrated with Linear](https://linear.app/now/how-cursor-integrated-with-linear-for-agents)
- [Linear GraphQL Schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql)
