import {execFile, execFileSync} from 'child_process';
import {existsSync, readFileSync} from 'fs';
import os from 'os';
import path from 'path';

import {Router} from 'express';

import type {ChatMessage, ChatMessageContent, FetchPlansResult} from '../../shared/types.js';

const router = Router();

// erk is installed in the project's .venv/bin — add it to PATH for child processes
const projectRoot = path.resolve(import.meta.dirname, '..', '..', '..', '..');
const venvBin = path.join(projectRoot, '.venv', 'bin');
const erkEnv = {...process.env, PATH: `${venvBin}:${process.env.PATH}`};

// Resolve GitHub username once at startup (gh auth is assumed)
const ghUsername = execFileSync('gh', ['api', 'user', '-q', '.login'], {
  encoding: 'utf-8',
}).trim();

router.get('/plans', (_req, res) => {
  execFile(
    'erk',
    ['exec', 'dash-data', '--creator', ghUsername],
    {env: erkEnv},
    (error, stdout, stderr) => {
      if (error) {
        const result: FetchPlansResult = {
          success: false,
          plans: [],
          count: 0,
          error: stderr || error.message,
        };
        res.json(result);
        return;
      }
      try {
        const data = JSON.parse(stdout);
        const result: FetchPlansResult = {
          success: true,
          plans: data.plans ?? data,
          count: data.count ?? (data.plans ?? data).length,
        };
        res.json(result);
      } catch (parseError) {
        const result: FetchPlansResult = {
          success: false,
          plans: [],
          count: 0,
          error: `Failed to parse erk output: ${parseError}`,
        };
        res.json(result);
      }
    },
  );
});

/**
 * Resolve the worktree path for a plan's branch by parsing `git worktree list --porcelain`.
 * Returns the worktree path if found, or null.
 */
function resolveWorktreePath(branch: string): string | null {
  try {
    const output = execFileSync('git', ['worktree', 'list', '--porcelain'], {
      cwd: projectRoot,
      encoding: 'utf-8',
    });
    let currentPath: string | null = null;
    for (const line of output.split('\n')) {
      if (line.startsWith('worktree ')) {
        currentPath = line.slice('worktree '.length);
      } else if (line.startsWith('branch refs/heads/') && currentPath) {
        if (line.slice('branch refs/heads/'.length) === branch) {
          return currentPath;
        }
      }
    }
  } catch {
    // git not available
  }
  return null;
}

/**
 * Look up a plan's worktree path by issue number via dash-data + git worktree list.
 */
function resolveWorktreePathForIssue(
  issueNumber: string,
  callback: (error: string | null, worktreePath: string | null) => void,
) {
  execFile(
    'erk',
    ['exec', 'dash-data', '--creator', ghUsername],
    {env: erkEnv},
    (dataError, dataStdout) => {
      if (dataError) {
        callback('Failed to fetch plan data', null);
        return;
      }
      try {
        const data = JSON.parse(dataStdout);
        const plans: Array<{issue_number: number; worktree_branch: string | null}> =
          data.plans ?? data;
        const plan = plans.find((p) => String(p.issue_number) === issueNumber);
        if (plan?.worktree_branch) {
          const wtPath = resolveWorktreePath(plan.worktree_branch);
          if (wtPath) {
            callback(null, wtPath);
            return;
          }
        }
        callback('Worktree not found locally', null);
      } catch {
        callback('Failed to parse plan data', null);
      }
    },
  );
}

// Resolve worktree path for a plan (lightweight, no mutation)
router.get('/plans/:issueNumber/worktree-path', (req, res) => {
  resolveWorktreePathForIssue(req.params.issueNumber, (error, worktreePath) => {
    if (error) {
      res.json({success: false, error});
    } else {
      res.json({success: true, worktreePath});
    }
  });
});

router.post('/plans/:issueNumber/prepare', (req, res) => {
  const {issueNumber} = req.params;

  execFile(
    'erk',
    ['prepare', '--create-only', issueNumber],
    {env: erkEnv, timeout: 60_000},
    (error, _stdout, stderr) => {
      if (error) {
        // "already exists" is expected if worktree was previously created
        const isAlreadyExists = stderr.includes('already exists');
        if (!isAlreadyExists) {
          res.json({success: false, error: stderr || error.message});
          return;
        }
      }

      resolveWorktreePathForIssue(issueNumber, (resolveError, worktreePath) => {
        if (resolveError) {
          // Fallback: worktree may be the root
          res.json({success: true, worktreePath: projectRoot});
        } else {
          res.json({success: true, worktreePath});
        }
      });
    },
  );
});

// Check implementation status in a plan's worktree
router.get('/plans/:issueNumber/impl-status', (req, res) => {
  resolveWorktreePathForIssue(req.params.issueNumber, (error, worktreePath) => {
    if (error || !worktreePath) {
      res.json({success: true, hasImpl: false, implValid: false});
      return;
    }
    execFile(
      'erk',
      ['exec', 'impl-init', '--json'],
      {env: erkEnv, cwd: worktreePath, timeout: 10_000},
      (implError, implStdout) => {
        if (implError) {
          res.json({success: true, hasImpl: false, implValid: false, worktreePath});
          return;
        }
        try {
          const data = JSON.parse(implStdout);
          res.json({
            success: true,
            hasImpl: true,
            implValid: data.valid === true,
            hasIssueTracking: data.has_issue_tracking === true,
            worktreePath,
          });
        } catch {
          res.json({success: true, hasImpl: false, implValid: false, worktreePath});
        }
      },
    );
  });
});

// List recent Claude Code sessions for a given working directory
router.get('/sessions', (req, res) => {
  const cwd = typeof req.query.cwd === 'string' ? req.query.cwd : undefined;
  if (!cwd) {
    res.json({success: false, error: 'cwd query parameter required'});
    return;
  }
  execFile(
    'erk',
    ['exec', 'list-sessions', '--limit', '10', '--min-size', '1000'],
    {env: erkEnv, cwd, timeout: 10_000},
    (error, stdout) => {
      if (error) {
        res.json({success: false, error: error.message, sessions: []});
        return;
      }
      try {
        const data = JSON.parse(stdout);
        res.json({
          success: true,
          sessions: (data.sessions ?? []).map(
            (s: {
              session_id: string;
              mtime_relative: string;
              summary: string;
              branch: string | null;
            }) => ({
              session_id: s.session_id,
              mtime_relative: s.mtime_relative,
              summary: s.summary,
              branch: s.branch,
            }),
          ),
        });
      } catch {
        res.json({success: false, error: 'Failed to parse sessions', sessions: []});
      }
    },
  );
});

/**
 * Find a session JSONL file by walking up from cwd to find the Claude projects directory.
 */
function findSessionFile(cwd: string, sessionId: string): string | null {
  // Validate session ID format (UUID)
  if (!/^[0-9a-f-]{36}$/.test(sessionId)) {
    return null;
  }

  const projectsDir = path.join(os.homedir(), '.claude', 'projects');
  let current = cwd;
  while (current !== path.dirname(current)) {
    const encoded = current.replaceAll('/', '-').replaceAll('.', '-');
    const sessionPath = path.join(projectsDir, encoded, `${sessionId}.jsonl`);
    if (existsSync(sessionPath)) {
      return sessionPath;
    }
    current = path.dirname(current);
  }
  return null;
}

/**
 * Parse a session JSONL file into ChatMessage array for the UI.
 */
function parseSessionMessages(filePath: string): ChatMessage[] {
  const messages: ChatMessage[] = [];
  const raw = readFileSync(filePath, 'utf-8');

  for (const line of raw.split('\n')) {
    if (!line.trim()) {
      continue;
    }
    let obj: Record<string, unknown>;
    try {
      obj = JSON.parse(line);
    } catch {
      continue;
    }
    const type = obj.type;
    if (type !== 'user' && type !== 'assistant') {
      continue;
    }

    const msg = obj.message as {role?: string; content?: unknown[]} | undefined;
    if (!msg?.content || !Array.isArray(msg.content)) {
      continue;
    }

    const content: ChatMessageContent[] = [];
    for (const block of msg.content) {
      if (typeof block !== 'object' || block === null || !('type' in block)) {
        continue;
      }
      const b = block as Record<string, unknown>;
      if (b.type === 'text' && typeof b.text === 'string') {
        content.push({type: 'text', text: b.text});
      } else if (b.type === 'tool_use' && typeof b.name === 'string') {
        content.push({
          type: 'tool_use',
          toolName: b.name,
          toolInput: (b.input as Record<string, unknown>) ?? {},
          toolUseId: (b.id as string) ?? '',
        });
      } else if (b.type === 'tool_result') {
        const resultContent = b.content;
        let output = '';
        if (typeof resultContent === 'string') {
          output = resultContent;
        } else if (Array.isArray(resultContent)) {
          output = resultContent
            .filter(
              (c: unknown) =>
                typeof c === 'object' &&
                c !== null &&
                (c as Record<string, unknown>).type === 'text',
            )
            .map((c: unknown) => (c as {text: string}).text)
            .join('\n');
        }
        content.push({
          type: 'tool_result',
          toolUseId: (b.tool_use_id as string) ?? '',
          output: output.slice(0, 5000),
          isError: (b.is_error as boolean) ?? false,
        });
      }
    }

    if (content.length > 0) {
      messages.push({
        role: type as 'user' | 'assistant',
        content,
        timestamp: 0,
      });
    }
  }
  return messages;
}

// Load messages from a previous session
router.get('/sessions/:sessionId/messages', (req, res) => {
  const cwd = typeof req.query.cwd === 'string' ? req.query.cwd : undefined;
  if (!cwd) {
    res.json({success: false, error: 'cwd query parameter required'});
    return;
  }
  const sessionPath = findSessionFile(cwd, req.params.sessionId);
  if (!sessionPath) {
    res.json({success: false, error: 'Session not found'});
    return;
  }
  try {
    const messages = parseSessionMessages(sessionPath);
    res.json({success: true, messages});
  } catch (err) {
    res.json({
      success: false,
      error: err instanceof Error ? err.message : 'Failed to read session',
    });
  }
});

export default router;
