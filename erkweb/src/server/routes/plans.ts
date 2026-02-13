import {execFile, execFileSync} from 'child_process';
import path from 'path';

import {Router} from 'express';

import type {ActionResult, FetchPlansResult} from '../../shared/types.js';

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

/**
 * Run a server-side erk command for a plan and return the result.
 */
function runErkCommand(
  args: string[],
  options: {cwd?: string; timeout?: number},
  callback: (result: ActionResult) => void,
) {
  execFile(
    'erk',
    args,
    {env: erkEnv, cwd: options.cwd, timeout: options.timeout ?? 120_000},
    (error, stdout, stderr) => {
      if (error) {
        callback({success: false, error: stderr || error.message});
      } else {
        callback({success: true, output: stdout.trim()});
      }
    },
  );
}

// Submit plan to queue
router.post('/plans/:issueNumber/submit', (req, res) => {
  runErkCommand(['plan', 'submit', req.params.issueNumber, '-f'], {timeout: 120_000}, (result) =>
    res.json(result),
  );
});

// Address PR feedback remotely
router.post('/plans/:issueNumber/address-remote', (req, res) => {
  // Need PR number - look it up from plans data
  resolveWorktreePathForIssue(req.params.issueNumber, (error, _worktreePath) => {
    if (error) {
      res.json({success: false, error});
      return;
    }
    // Get PR number from dash-data
    execFile(
      'erk',
      ['exec', 'dash-data', '--creator', ghUsername],
      {env: erkEnv},
      (dataError, dataStdout) => {
        if (dataError) {
          res.json({success: false, error: 'Failed to fetch plan data'});
          return;
        }
        try {
          const data = JSON.parse(dataStdout);
          const plans: Array<{issue_number: number; pr_number: number | null}> = data.plans ?? data;
          const plan = plans.find((p) => String(p.issue_number) === req.params.issueNumber);
          if (!plan?.pr_number) {
            res.json({success: false, error: 'No PR found for this plan'});
            return;
          }
          runErkCommand(
            ['launch', 'pr-address', '--pr', String(plan.pr_number)],
            {timeout: 120_000},
            (result) => res.json(result),
          );
        } catch {
          res.json({success: false, error: 'Failed to parse plan data'});
        }
      },
    );
  });
});

// Fix conflicts remotely
router.post('/plans/:issueNumber/fix-conflicts', (req, res) => {
  resolveWorktreePathForIssue(req.params.issueNumber, (error, _worktreePath) => {
    if (error) {
      res.json({success: false, error});
      return;
    }
    execFile(
      'erk',
      ['exec', 'dash-data', '--creator', ghUsername],
      {env: erkEnv},
      (dataError, dataStdout) => {
        if (dataError) {
          res.json({success: false, error: 'Failed to fetch plan data'});
          return;
        }
        try {
          const data = JSON.parse(dataStdout);
          const plans: Array<{issue_number: number; pr_number: number | null}> = data.plans ?? data;
          const plan = plans.find((p) => String(p.issue_number) === req.params.issueNumber);
          if (!plan?.pr_number) {
            res.json({success: false, error: 'No PR found for this plan'});
            return;
          }
          runErkCommand(
            ['launch', 'pr-fix-conflicts', '--pr', String(plan.pr_number)],
            {timeout: 120_000},
            (result) => res.json(result),
          );
        } catch {
          res.json({success: false, error: 'Failed to parse plan data'});
        }
      },
    );
  });
});

// Land PR
router.post('/plans/:issueNumber/land', (req, res) => {
  resolveWorktreePathForIssue(req.params.issueNumber, (error, _worktreePath) => {
    if (error) {
      res.json({success: false, error});
      return;
    }
    execFile(
      'erk',
      ['exec', 'dash-data', '--creator', ghUsername],
      {env: erkEnv},
      (dataError, dataStdout) => {
        if (dataError) {
          res.json({success: false, error: 'Failed to fetch plan data'});
          return;
        }
        try {
          const data = JSON.parse(dataStdout);
          const plans: Array<{
            issue_number: number;
            pr_number: number | null;
            pr_head_branch: string | null;
          }> = data.plans ?? data;
          const plan = plans.find((p) => String(p.issue_number) === req.params.issueNumber);
          if (!plan?.pr_number || !plan?.pr_head_branch) {
            res.json({success: false, error: 'No PR or branch found for this plan'});
            return;
          }
          runErkCommand(
            [
              'exec',
              'land-execute',
              `--pr-number=${plan.pr_number}`,
              `--branch=${plan.pr_head_branch}`,
              '-f',
            ],
            {timeout: 120_000},
            (result) => res.json(result),
          );
        } catch {
          res.json({success: false, error: 'Failed to parse plan data'});
        }
      },
    );
  });
});

// Close plan
router.post('/plans/:issueNumber/close', (req, res) => {
  runErkCommand(['plan', 'close', req.params.issueNumber], {timeout: 30_000}, (result) =>
    res.json(result),
  );
});

export default router;
