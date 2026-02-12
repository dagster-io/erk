import {execFile, execFileSync} from 'child_process';

import {Router} from 'express';

import type {FetchPlansResult} from '../../shared/types.js';

const router = Router();

// Resolve GitHub username once at startup (gh auth is assumed)
const ghUsername = execFileSync('gh', ['api', 'user', '-q', '.login'], {
  encoding: 'utf-8',
}).trim();

router.get('/plans', (_req, res) => {
  execFile('erk', ['exec', 'dash-data', '--creator', ghUsername], (error, stdout, stderr) => {
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
  });
});

export default router;
