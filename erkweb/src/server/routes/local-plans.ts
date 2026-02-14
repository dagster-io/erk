import fs from 'fs';
import os from 'os';
import path from 'path';

import {Router} from 'express';

import type {LocalPlanDetail, LocalPlanFile, PlanAnnotation} from '../../shared/types.js';

const router = Router();

const plansDir = path.join(os.homedir(), '.claude', 'plans');

function getPlansDir(): string {
  return plansDir;
}

/**
 * Extract title from first H1 line in markdown content.
 */
function extractTitle(content: string): string {
  const match = content.match(/^#\s+(.+)$/m);
  return match ? match[1].trim() : 'Untitled';
}

// List local plan files
router.get('/local-plans', (_req, res) => {
  const dir = getPlansDir();

  if (!fs.existsSync(dir)) {
    res.json({success: true, plans: []});
    return;
  }

  try {
    const files = fs.readdirSync(dir).filter((f) => f.endsWith('.md') && !f.endsWith('-review.md'));

    const plans: LocalPlanFile[] = files.map((f) => {
      const fullPath = path.join(dir, f);
      const stat = fs.statSync(fullPath);
      const content = fs.readFileSync(fullPath, 'utf-8');
      const slug = f.replace(/\.md$/, '');

      let commentCount = 0;
      const reviewJsonPath = path.join(dir, `${slug}-review.json`);
      if (fs.existsSync(reviewJsonPath)) {
        try {
          const raw = fs.readFileSync(reviewJsonPath, 'utf-8');
          const annotations = JSON.parse(raw);
          if (Array.isArray(annotations)) {
            commentCount = annotations.length;
          }
        } catch {
          // Ignore malformed review files
        }
      }

      return {
        slug,
        title: extractTitle(content),
        modifiedAt: stat.mtimeMs,
        commentCount,
      };
    });

    // Sort by modification time descending
    plans.sort((a, b) => b.modifiedAt - a.modifiedAt);

    res.json({success: true, plans});
  } catch (err) {
    res.json({success: false, error: err instanceof Error ? err.message : 'Failed to list plans'});
  }
});

// Get a single local plan
router.get('/local-plans/:slug', (req, res) => {
  const {slug} = req.params;
  const filePath = path.join(getPlansDir(), `${slug}.md`);

  if (!fs.existsSync(filePath)) {
    res.status(404).json({success: false, error: 'Plan not found'});
    return;
  }

  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    const detail: LocalPlanDetail = {
      slug,
      title: extractTitle(content),
      content,
    };

    res.json({success: true, plan: detail});
  } catch (err) {
    res.json({success: false, error: err instanceof Error ? err.message : 'Failed to read plan'});
  }
});

// Load existing review annotations for a plan
router.get('/local-plans/:slug/review', (req, res) => {
  const {slug} = req.params;
  const jsonPath = path.join(getPlansDir(), `${slug}-review.json`);

  if (!fs.existsSync(jsonPath)) {
    res.json({success: true, annotations: []});
    return;
  }

  try {
    const raw = fs.readFileSync(jsonPath, 'utf-8');
    const annotations = JSON.parse(raw) as PlanAnnotation[];
    res.json({success: true, annotations});
  } catch (err) {
    res.json({success: false, error: err instanceof Error ? err.message : 'Failed to load review'});
  }
});

// Save a review for a plan
router.post('/local-plans/:slug/review', (req, res) => {
  const {slug} = req.params;
  const {annotations} = req.body as {annotations: PlanAnnotation[]};

  if (!annotations || !Array.isArray(annotations)) {
    res.status(400).json({success: false, error: 'annotations array required'});
    return;
  }

  const planPath = path.join(getPlansDir(), `${slug}.md`);
  if (!fs.existsSync(planPath)) {
    res.status(404).json({success: false, error: 'Plan not found'});
    return;
  }

  try {
    const planContent = fs.readFileSync(planPath, 'utf-8');
    const title = extractTitle(planContent);
    const planLines = planContent.split('\n');

    const lines: string[] = [`# Plan Review: ${title}`, ''];

    for (const annotation of annotations) {
      lines.push('---', '');

      const rangeLabel =
        annotation.startLine === annotation.endLine
          ? `Line ${annotation.startLine}`
          : `Lines ${annotation.startLine}-${annotation.endLine}`;

      lines.push(`## ${rangeLabel}`);
      lines.push('');

      // Quote the actual lines from the plan content
      const start = Math.max(0, annotation.startLine - 1);
      const end = Math.min(planLines.length, annotation.endLine);
      for (let i = start; i < end; i++) {
        lines.push(`> ${planLines[i]}`);
      }
      lines.push('');
      lines.push(`**Comment:** ${annotation.comment}`);
      lines.push('');
    }

    lines.push('---', '');

    const reviewPath = path.join(getPlansDir(), `${slug}-review.md`);
    fs.writeFileSync(reviewPath, lines.join('\n'), 'utf-8');

    // Also save structured JSON for round-tripping
    const jsonPath = path.join(getPlansDir(), `${slug}-review.json`);
    fs.writeFileSync(jsonPath, JSON.stringify(annotations, null, 2), 'utf-8');

    res.json({success: true, reviewPath});
  } catch (err) {
    res.json({success: false, error: err instanceof Error ? err.message : 'Failed to save review'});
  }
});

export default router;
