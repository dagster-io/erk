---
title: Linear Agent-Native Primitives
description: Linear's agent-native primitives for AI-assisted development
read_when:
  - Considering Linear as an alternative to GitHub Issues
  - Building a Linear gateway for erk
  - Understanding how other tools (Cursor, Devin) integrate with Linear
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

Or proactively via GraphQL mutations:

- `agentSessionCreateOnIssue` - Create session linked to an issue
- `agentSessionCreateOnComment` - Create session linked to a comment thread

### Key Session Fields

```graphql
type AgentSession {
  id: ID!
  status: AgentSessionStatus!

  # Relationships
  appUser: User! # The agent
  creator: User # Human who triggered (null if automated)
  issue: Issue # Associated issue
  comment: Comment # Associated comment thread
  # Context
  promptContext: String # Pre-formatted context for agent
  plan: JSON # Agent's execution strategy
  summary: String # Summary of activities
  # Lifecycle
  startedAt: DateTime
  endedAt: DateTime

  # External links
  externalUrls: JSON! # Links to PRs, external resources
  # Activities
  activities: AgentActivityConnection!
  pullRequests: AgentSessionToPullRequestConnection!
}
```

### State Management

Linear manages session state automatically based on emitted activities. You don't need to manually update status - it transitions based on what activities you emit.

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

### Activity Fields

```graphql
type AgentActivity {
  id: ID!
  agentSession: AgentSession!
  content: AgentActivityContent! # Union of content types
  ephemeral: Boolean! # Disappears after next activity
  signal: AgentActivitySignal # Modifier (auth, continue, select, stop)
  signalMetadata: JSON
  sourceComment: Comment # If linked to a comment
  user: User! # Who created this activity
}
```

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

### Action Activity Content

For `action` type activities, the content includes:

```graphql
type AgentActivityActionContent {
  action: String! # The action being performed (e.g., "read_file")
  parameter: String! # Parameters (e.g., file path)
  result: String # Result in Markdown (optional)
  type: AgentActivityType!
}
```

## Guidance System

Linear provides cascading configuration for agent behavior.

### Guidance Hierarchy

```
Workspace guidance (lowest precedence)
    └── Parent team guidance
        └── Current team guidance (highest precedence)
```

The nearest team-specific guidance takes precedence. This allows organization-wide defaults with team-level overrides.

### Guidance in Webhooks

When an `AgentSessionEvent` webhook fires, it includes:

```graphql
type AgentSessionEventWebhookPayload {
  guidance: [GuidanceRuleWebhookPayload!]
  # ...
}

type GuidanceRuleWebhookPayload {
  body: String! # Guidance content in Markdown
  origin: GuidanceRuleOriginWebhookPayload! # Organization or Team
}
```

This is like **system prompts managed in Linear**, per-team. Agents receive behavior instructions without needing them hardcoded.

## promptContext

Linear pre-formats context for agents in the `promptContext` field.

### What It Contains

On `AgentSessionEvent` webhooks (for `created` events):

```
promptContext: String containing:
  - Issue title, description, properties
  - Relevant comments
  - Cascading guidance from team/workspace
  - Thread context if applicable
```

### Why It Matters

Agents receive **ready-to-use context**, not raw data to parse. This eliminates the need for agents to make multiple API calls to understand what they're working on.

## Webhook Events

### AgentSessionEvent

Sent when agent sessions are created or updated.

```graphql
type AgentSessionEventWebhookPayload {
  action: String! # "created" or "updated"
  agentSession: AgentSessionWebhookPayload!
  agentActivity: AgentActivityWebhookPayload # If activity triggered event
  appUserId: String!
  oauthClientId: String!
  organizationId: String!

  # Context (created events only)
  promptContext: String
  guidance: [GuidanceRuleWebhookPayload!]
  previousComments: [CommentChildWebhookPayload!]
}
```

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

21 tools for issue/project management:

- Create/update issues
- Query issues with filters
- Manage projects and teams
- Add comments
- Update properties

This enables Claude Code to interact with Linear directly without going through erk CLI.

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

### Create Agent Session on Issue

```graphql
mutation CreateAgentSession(
  $issueId: String!
  $externalUrls: [AgentSessionExternalUrlInput!]
) {
  agentSessionCreateOnIssue(
    input: { issueId: $issueId, externalUrls: $externalUrls }
  ) {
    success
    agentSession {
      id
      status
      startedAt
    }
  }
}
```

### Emit Agent Activity

```graphql
mutation EmitActivity($input: AgentActivityCreateInput!) {
  agentActivityCreate(input: $input) {
    success
    agentActivity {
      id
      content
    }
  }
}
```

Input structure:

```graphql
input AgentActivityCreateInput {
  agentSessionId: String!
  content: JSONObject! # Activity content (type-specific)
  ephemeral: Boolean # Default false
  signal: AgentActivitySignal # Optional modifier
}
```

### Complete Agent Session

Update session with summary and final external URLs:

```graphql
mutation UpdateSession($id: String!, $input: AgentSessionUpdateInput!) {
  agentSessionUpdate(id: $id, input: $input) {
    success
    agentSession {
      status
      summary
    }
  }
}
```

## Sources

- [Linear for Agents](https://linear.app/agents)
- [Agent Interaction Guidelines](https://linear.app/developers/aig)
- [Agent Interaction SDK blog](https://linear.app/now/our-approach-to-building-the-agent-interaction-sdk)
- [How Cursor integrated with Linear](https://linear.app/now/how-cursor-integrated-with-linear-for-agents)
- [Linear GraphQL Schema](https://github.com/linear/linear/blob/master/packages/sdk/src/schema.graphql)
