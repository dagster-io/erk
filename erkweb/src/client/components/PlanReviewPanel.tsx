import Prism from 'prismjs';
import 'prismjs/components/prism-markdown';
import {useEffect, useMemo, useRef, useState} from 'react';

import type {LocalPlanDetail, PlanAnnotation} from '../../shared/types.js';
import './PlanReviewPanel.css';

interface PlanReviewPanelProps {
  plan: LocalPlanDetail;
}

export function PlanReviewPanel({plan}: PlanReviewPanelProps) {
  const [annotations, setAnnotations] = useState<PlanAnnotation[]>([]);

  // Load existing annotations on mount / plan change
  useEffect(() => {
    setAnnotations([]);
    fetch(`/api/local-plans/${encodeURIComponent(plan.slug)}/review`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success && Array.isArray(data.annotations) && data.annotations.length > 0) {
          setAnnotations(data.annotations);
        }
      })
      .catch(() => {
        // Silently ignore load failures
      });
  }, [plan.slug]);

  function saveAnnotations(next: PlanAnnotation[]) {
    setAnnotations(next);
    fetch(`/api/local-plans/${encodeURIComponent(plan.slug)}/review`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({annotations: next}),
    }).catch(() => {
      // Silently ignore save failures
    });
  }

  // Selection state
  const [anchorLine, setAnchorLine] = useState<number | null>(null);
  const [selStart, setSelStart] = useState<number | null>(null);
  const [selEnd, setSelEnd] = useState<number | null>(null);

  // Inline comment form
  const [commentFormAt, setCommentFormAt] = useState<number | null>(null); // line after which form appears
  const [commentText, setCommentText] = useState('');

  // Editing existing annotation
  const [editingIndex, setEditingIndex] = useState<number | null>(null);

  const lines = plan.content.split('\n');

  // Highlight the full content with Prism, then split back into per-line HTML
  const highlightedLines = useMemo(() => {
    const html = Prism.highlight(plan.content, Prism.languages.markdown, 'markdown');
    return html.split('\n');
  }, [plan.content]);

  // Drag selection state
  const dragging = useRef(false);
  const dragAnchor = useRef<number | null>(null);

  function handleGutterMouseDown(lineNum: number, shiftKey: boolean) {
    if (shiftKey && anchorLine !== null) {
      const start = Math.min(anchorLine, lineNum);
      const end = Math.max(anchorLine, lineNum);
      setSelStart(start);
      setSelEnd(end);
      setCommentFormAt(end);
      setCommentText('');
      setEditingIndex(null);
    } else {
      dragging.current = true;
      dragAnchor.current = lineNum;
      setAnchorLine(lineNum);
      setSelStart(lineNum);
      setSelEnd(lineNum);
      setCommentFormAt(null);
      setCommentText('');
      setEditingIndex(null);
    }
  }

  function handleGutterMouseEnter(lineNum: number) {
    if (!dragging.current || dragAnchor.current === null) {
      return;
    }
    const start = Math.min(dragAnchor.current, lineNum);
    const end = Math.max(dragAnchor.current, lineNum);
    setSelStart(start);
    setSelEnd(end);
  }

  // Global mouseup to end drag
  useEffect(() => {
    function handleMouseUp() {
      if (dragging.current) {
        dragging.current = false;
        // Show comment form at end of selection
        setSelEnd((prev) => {
          if (prev !== null) {
            setCommentFormAt(prev);
          }
          return prev;
        });
      }
    }
    window.addEventListener('mouseup', handleMouseUp);
    return () => window.removeEventListener('mouseup', handleMouseUp);
  }, []);

  function handleCancelComment() {
    setSelStart(null);
    setSelEnd(null);
    setAnchorLine(null);
    setCommentFormAt(null);
    setCommentText('');
    setEditingIndex(null);
  }

  function handleSaveComment() {
    if (commentText.trim() === '' || selStart === null || selEnd === null) {
      return;
    }

    if (editingIndex !== null) {
      const next = annotations.map((a, i) =>
        i === editingIndex
          ? {...a, startLine: selStart, endLine: selEnd, comment: commentText.trim()}
          : a,
      );
      saveAnnotations(next);
    } else {
      const annotation: PlanAnnotation = {
        startLine: selStart,
        endLine: selEnd,
        comment: commentText.trim(),
      };
      saveAnnotations([...annotations, annotation]);
    }
    handleCancelComment();
  }

  function handleEditAnnotation(index: number) {
    const a = annotations[index];
    setSelStart(a.startLine);
    setSelEnd(a.endLine);
    setAnchorLine(a.startLine);
    setCommentFormAt(a.endLine);
    setCommentText(a.comment);
    setEditingIndex(index);
  }

  function handleDeleteAnnotation(index: number) {
    saveAnnotations(annotations.filter((_, i) => i !== index));
  }

  // Build a map of annotations keyed by the line they appear after (endLine)
  const annotationsByEndLine = new Map<number, {annotation: PlanAnnotation; index: number}[]>();
  for (let i = 0; i < annotations.length; i++) {
    const a = annotations[i];
    const existing = annotationsByEndLine.get(a.endLine) ?? [];
    existing.push({annotation: a, index: i});
    annotationsByEndLine.set(a.endLine, existing);
  }

  const [copied, setCopied] = useState(false);

  function formatReviewMarkdown(): string {
    const parts: string[] = [`# Plan Review: ${plan.title}`, ''];
    for (const a of annotations) {
      const rangeLabel =
        a.startLine === a.endLine ? `Line ${a.startLine}` : `Lines ${a.startLine}-${a.endLine}`;
      parts.push(`## ${rangeLabel}`, '');
      const start = Math.max(0, a.startLine - 1);
      const end = Math.min(lines.length, a.endLine);
      for (let i = start; i < end; i++) {
        parts.push(`> ${lines[i]}`);
      }
      parts.push('', `**Comment:** ${a.comment}`, '');
    }
    return parts.join('\n');
  }

  function handleCopyReview() {
    navigator.clipboard.writeText(formatReviewMarkdown()).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    });
  }

  function isLineSelected(lineNum: number): boolean {
    if (selStart === null || selEnd === null) {
      return false;
    }
    return lineNum >= selStart && lineNum <= selEnd;
  }

  return (
    <div className="plan-review-panel">
      <div className="review-header">
        <div className="review-header-left">
          <span className="review-title">{plan.title}</span>
          <span className="review-slug">{plan.slug}</span>
        </div>
      </div>
      <div className="review-body">
        <div className="line-table">
          {lines.map((_line, i) => {
            const lineNum = i + 1;
            const selected = isLineSelected(lineNum);
            const endAnnotations = annotationsByEndLine.get(lineNum);
            const showFormHere = commentFormAt === lineNum;
            const lineHtml = highlightedLines[i] || '\u00A0';

            return (
              <div key={lineNum}>
                <div className={`line-row ${selected ? 'line-selected' : ''}`}>
                  <div
                    className="line-gutter"
                    onMouseDown={(e) => handleGutterMouseDown(lineNum, e.shiftKey)}
                    onMouseEnter={() => handleGutterMouseEnter(lineNum)}
                    title="Click to comment, drag or shift+click for range"
                  >
                    <span className="line-gutter-plus">+</span>
                    <span className="line-number">{lineNum}</span>
                  </div>
                  <code className="line-content" dangerouslySetInnerHTML={{__html: lineHtml}} />
                </div>

                {/* Existing annotations that end on this line */}
                {endAnnotations &&
                  !showFormHere &&
                  endAnnotations.map(({annotation: a, index: idx}) => (
                    <div key={`ann-${idx}`} className="annotation-block">
                      <div className="annotation-range">
                        {a.startLine === a.endLine
                          ? `Line ${a.startLine}`
                          : `Lines ${a.startLine}-${a.endLine}`}
                      </div>
                      <div className="annotation-text">{a.comment}</div>
                      <div className="annotation-actions">
                        <button
                          className="annotation-btn"
                          onClick={() => handleEditAnnotation(idx)}
                        >
                          Edit
                        </button>
                        <button
                          className="annotation-btn annotation-btn-delete"
                          onClick={() => handleDeleteAnnotation(idx)}
                        >
                          Delete
                        </button>
                      </div>
                    </div>
                  ))}

                {/* Comment form */}
                {showFormHere && (
                  <div className="comment-form">
                    <div className="comment-form-range">
                      {selStart === selEnd
                        ? `Commenting on line ${selStart}`
                        : `Commenting on lines ${selStart}-${selEnd}`}
                    </div>
                    <textarea
                      className="comment-form-input"
                      value={commentText}
                      onChange={(e) => setCommentText(e.target.value)}
                      placeholder="Add your comment..."
                      rows={3}
                      autoFocus
                    />
                    <div className="comment-form-actions">
                      <button
                        className="comment-form-save"
                        onClick={handleSaveComment}
                        disabled={commentText.trim() === ''}
                      >
                        {editingIndex !== null ? 'Update' : 'Comment'}
                      </button>
                      <button className="comment-form-cancel" onClick={handleCancelComment}>
                        Cancel
                      </button>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
      {annotations.length > 0 && (
        <div className="review-footer">
          <span className="review-annotation-count">
            {annotations.length} comment{annotations.length !== 1 ? 's' : ''}
          </span>
          <button className="review-copy-btn" onClick={handleCopyReview}>
            <span style={{visibility: copied ? 'hidden' : 'visible'}}>Copy review for Claude</span>
            {copied && <span className="review-copy-btn-overlay">Copied!</span>}
          </button>
        </div>
      )}
    </div>
  );
}
