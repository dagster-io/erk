import {dirname} from 'path';

import {
  type PermissionUpdate,
  type Query,
  type SDKMessage,
  query,
} from '@anthropic-ai/claude-agent-sdk';
import type {WebSocket} from 'ws';

import type {ClientMessage, ServerMessage} from '../../shared/types.js';
import {discoverCommands} from '../commands.js';

// Build a clean env for spawning Claude Code processes.
// - Ensures the running node binary's directory is in PATH (fixes ENOENT on cwd change)
// - Excludes CLAUDECODE to prevent "nested session" detection when starting fresh sessions
const nodeDir = dirname(process.execPath);
function buildQueryEnv(): Record<string, string> {
  const env: Record<string, string> = {};
  for (const [key, value] of Object.entries(process.env)) {
    if (value !== undefined && key !== 'CLAUDECODE') {
      env[key] = value;
    }
  }
  env.PATH = env.PATH ? `${nodeDir}:${env.PATH}` : nodeDir;
  return env;
}

interface PermissionResponse {
  allowed: boolean;
  applyAlways: boolean;
}

function send(ws: WebSocket, msg: ServerMessage) {
  if (ws.readyState === ws.OPEN) {
    ws.send(JSON.stringify(msg));
  }
}

export function handleChatConnection(ws: WebSocket) {
  let sessionId: string | null = null;
  let activeQuery: Query | null = null;
  const pendingPermissions = new Map<string, (response: PermissionResponse) => void>();
  const pendingSuggestions = new Map<string, PermissionUpdate[] | undefined>();

  // Send available commands immediately on connect (before any query)
  const cwd = process.env.ERKWEB_CWD || process.cwd();
  discoverCommands(cwd)
    .then((commands) => {
      send(ws, {
        type: 'chat_commands',
        commands: commands.map((c) => ({
          name: c.name,
          description: c.description,
          argumentHint: c.argumentHint,
        })),
      });
    })
    .catch(() => {});

  ws.on('message', async (data) => {
    let msg: ClientMessage;
    try {
      msg = JSON.parse(data.toString());
    } catch {
      send(ws, {type: 'chat_error', message: 'Invalid JSON'});
      return;
    }

    if (msg.type === 'permission_response') {
      const resolve = pendingPermissions.get(msg.toolUseId);
      if (resolve) {
        pendingPermissions.delete(msg.toolUseId);
        resolve({allowed: msg.allowed, applyAlways: msg.applyAlways});
      }
      return;
    }

    if (msg.type === 'chat_stop') {
      if (activeQuery) {
        try {
          await activeQuery.interrupt();
        } catch {
          // ignore interrupt errors
        }
        activeQuery.close();
        activeQuery = null;
      }
      // Reject all pending permission requests
      for (const [id, resolve] of pendingPermissions) {
        resolve({allowed: false, applyAlways: false});
        pendingPermissions.delete(id);
      }
      pendingSuggestions.clear();
      return;
    }

    if (msg.type === 'chat_send') {
      const cwd = msg.cwd || process.env.ERKWEB_CWD || process.cwd();
      const permissionMode =
        (process.env.ERKWEB_PERMISSION_MODE as 'default' | 'acceptEdits' | 'bypassPermissions') ||
        'default';

      const resumeId = msg.newSession ? undefined : msg.resumeSessionId || sessionId || undefined;

      try {
        activeQuery = query({
          prompt: msg.text,
          options: {
            cwd,
            env: buildQueryEnv(),
            resume: resumeId,
            includePartialMessages: true,
            settingSources: ['user', 'project'],
            systemPrompt: {type: 'preset', preset: 'claude_code'},
            permissionMode,
            canUseTool: async (toolName, input, options) => {
              const toolUseId = options.toolUseID;

              pendingSuggestions.set(toolUseId, options.suggestions);

              send(ws, {
                type: 'permission_request',
                toolUseId,
                toolName,
                toolInput: input,
                reason: options.decisionReason,
                hasSuggestions:
                  Array.isArray(options.suggestions) && options.suggestions.length > 0,
              });

              const response = await new Promise<PermissionResponse>((resolve) => {
                pendingPermissions.set(toolUseId, resolve);
              });

              const suggestions = pendingSuggestions.get(toolUseId);
              pendingSuggestions.delete(toolUseId);

              if (response.allowed) {
                const result: {
                  behavior: 'allow';
                  updatedInput: Record<string, unknown>;
                  updatedPermissions?: PermissionUpdate[];
                  toolUseID: string;
                } = {behavior: 'allow', updatedInput: input, toolUseID: toolUseId};
                if (response.applyAlways && suggestions) {
                  result.updatedPermissions = suggestions;
                }
                return result;
              }
              return {behavior: 'deny', message: 'Denied by user.', toolUseID: toolUseId};
            },
          },
        });

        for await (const sdkMsg of activeQuery) {
          handleSDKMessage(ws, sdkMsg);
        }
      } catch (err) {
        send(ws, {
          type: 'chat_error',
          message: err instanceof Error ? err.message : String(err),
        });
      } finally {
        activeQuery = null;
      }
    }
  });

  ws.on('close', () => {
    if (activeQuery) {
      activeQuery.close();
      activeQuery = null;
    }
    // Clean up pending permissions on disconnect
    for (const [id, resolve] of pendingPermissions) {
      resolve({allowed: false, applyAlways: false});
      pendingPermissions.delete(id);
    }
    pendingSuggestions.clear();
  });

  function handleSDKMessage(ws: WebSocket, sdkMsg: SDKMessage) {
    switch (sdkMsg.type) {
      case 'system': {
        if (sdkMsg.subtype === 'init') {
          sessionId = sdkMsg.session_id;
          send(ws, {
            type: 'chat_init',
            sessionId: sdkMsg.session_id,
            model: sdkMsg.model,
          });
          // Fetch available slash commands asynchronously
          activeQuery
            ?.supportedCommands()
            .then((commands) => {
              send(ws, {
                type: 'chat_commands',
                commands: commands.map((c) => ({
                  name: c.name,
                  description: c.description,
                  argumentHint: c.argumentHint,
                })),
              });
            })
            .catch(() => {});
        }
        break;
      }

      case 'stream_event': {
        // SDKPartialAssistantMessage — token-level streaming
        const event = sdkMsg.event;
        if (event.type === 'content_block_delta' && event.delta.type === 'text_delta') {
          send(ws, {type: 'chat_partial', text: event.delta.text});
        }
        break;
      }

      case 'assistant': {
        // SDKAssistantMessage — complete message with all content blocks
        const content = sdkMsg.message.content;
        for (const block of content) {
          if (block.type === 'text') {
            send(ws, {type: 'chat_text', fullText: block.text});
          } else if (block.type === 'tool_use') {
            send(ws, {
              type: 'chat_tool_use',
              toolName: block.name,
              toolInput: block.input as Record<string, unknown>,
              toolUseId: block.id,
            });
          }
        }
        break;
      }

      case 'user': {
        // SDKUserMessage — contains tool results
        const message = sdkMsg.message;
        if (Array.isArray(message.content)) {
          for (const block of message.content) {
            if (typeof block === 'object' && 'type' in block && block.type === 'tool_result') {
              const content = block.content;
              let output = '';
              if (typeof content === 'string') {
                output = content;
              } else if (Array.isArray(content)) {
                output = content
                  .filter(
                    (c): c is {type: 'text'; text: string} =>
                      typeof c === 'object' && 'type' in c && c.type === 'text',
                  )
                  .map((c) => c.text)
                  .join('\n');
              }
              send(ws, {
                type: 'chat_tool_result',
                toolUseId: block.tool_use_id,
                output: output.slice(0, 5000), // truncate for UI
                isError: block.is_error ?? false,
              });
            }
          }
        }
        break;
      }

      case 'tool_progress': {
        send(ws, {
          type: 'chat_tool_progress',
          toolUseId: sdkMsg.tool_use_id,
          toolName: sdkMsg.tool_name,
          elapsedSeconds: sdkMsg.elapsed_time_seconds,
        });
        break;
      }

      case 'result': {
        // SDKResultMessage
        send(ws, {
          type: 'chat_done',
          numTurns: sdkMsg.num_turns,
          costUsd: sdkMsg.total_cost_usd,
        });
        break;
      }
    }
  }
}
