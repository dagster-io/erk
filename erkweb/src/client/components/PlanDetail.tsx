import {Box, Button, Colors, Icon, Tag} from '@dagster-io/ui-components';
import {useState} from 'react';

import styles from './PlanDetail.module.css';
import type {ActionResult, PlanRow} from '../../shared/types.js';

interface PlanDetailProps {
  plan: PlanRow;
  onClose: () => void;
}

type ActionState = 'idle' | 'running' | 'success' | 'error';

interface ActionStatus {
  state: ActionState;
  message?: string;
}

async function runAction(issueNumber: number, action: string): Promise<ActionResult> {
  const res = await fetch(`/api/plans/${issueNumber}/${action}`, {method: 'POST'});
  return res.json();
}

function copyToClipboard(text: string, setToast: (msg: string) => void) {
  navigator.clipboard.writeText(text).then(
    () => setToast('Copied!'),
    () => setToast('Copy failed'),
  );
}

export function PlanDetail({plan, onClose}: PlanDetailProps) {
  const [actionStatuses, setActionStatuses] = useState<Record<string, ActionStatus>>({});
  const [toast, setToast] = useState<string | null>(null);

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  }

  async function executeAction(actionKey: string) {
    setActionStatuses((prev) => ({...prev, [actionKey]: {state: 'running'}}));
    try {
      const result = await runAction(plan.issue_number, actionKey);
      if (result.success) {
        setActionStatuses((prev) => ({
          ...prev,
          [actionKey]: {state: 'success', message: result.output},
        }));
      } else {
        setActionStatuses((prev) => ({
          ...prev,
          [actionKey]: {state: 'error', message: result.error},
        }));
      }
    } catch (err) {
      setActionStatuses((prev) => ({
        ...prev,
        [actionKey]: {
          state: 'error',
          message: err instanceof Error ? err.message : 'Request failed',
        },
      }));
    }
  }

  const isMerged = plan.pr_state === 'merged';
  const hasPR = plan.pr_number !== null;
  const hasComments = !plan.comments_display.endsWith('/0');

  return (
    <Box
      flex={{direction: 'column'}}
      style={{height: '100%'}}
      background={Colors.backgroundLighter()}
    >
      <Box
        flex={{direction: 'row', justifyContent: 'space-between', alignItems: 'center'}}
        padding={{horizontal: 16, vertical: 8}}
        background={Colors.backgroundLighterHover()}
        border="bottom"
        style={{flexShrink: 0}}
      >
        <span className={styles.title}>
          #{plan.issue_number} {plan.title}
        </span>
        <Button icon={<Icon name="close" />} onClick={onClose} />
      </Box>
      <div className={styles.content}>
        {/* Issue - full width */}
        <div className={styles.section}>
          <div className={styles.label}>Issue</div>
          <div className={styles.value}>
            {plan.issue_url ? (
              <a href={plan.issue_url} target="_blank" rel="noopener noreferrer">
                #{plan.issue_number} - {plan.full_title}
              </a>
            ) : (
              plan.full_title
            )}
          </div>
        </div>

        {/* Metadata grid */}
        <div className={styles.grid}>
          <div className={styles.cell}>
            <div className={styles.label}>PR</div>
            <div className={styles.value}>
              {plan.pr_url ? (
                <a href={plan.pr_url} target="_blank" rel="noopener noreferrer">
                  {plan.pr_display}
                </a>
              ) : (
                <span className={styles.muted}>{plan.pr_display || 'None'}</span>
              )}
              {plan.pr_state && (
                <Tag
                  intent={
                    plan.pr_state === 'open'
                      ? 'success'
                      : plan.pr_state === 'merged'
                        ? 'primary'
                        : 'danger'
                  }
                >
                  {plan.pr_state}
                </Tag>
              )}
            </div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Checks</div>
            <div className={styles.value}>{plan.checks_display || '-'}</div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Comments</div>
            <div className={styles.value}>{plan.comments_display || '-'}</div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Objective</div>
            <div className={styles.value}>
              {plan.objective_display || <span className={styles.muted}>None</span>}
            </div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Worktree</div>
            <div className={styles.value}>
              <code>{plan.worktree_name}</code>
              <Tag intent={plan.exists_locally ? 'success' : 'none'}>
                {plan.exists_locally ? 'local' : 'remote only'}
              </Tag>
            </div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Branch</div>
            <div className={styles.value}>
              {plan.worktree_branch ? (
                <code>{plan.worktree_branch}</code>
              ) : (
                <span className={styles.muted}>-</span>
              )}
            </div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Implementation</div>
            <div className={styles.value}>
              L: {plan.local_impl_display || '-'} / R: {plan.remote_impl_display || '-'}
            </div>
          </div>

          <div className={styles.cell}>
            <div className={styles.label}>Run</div>
            <div className={styles.value}>
              {plan.run_url ? (
                <a href={plan.run_url} target="_blank" rel="noopener noreferrer">
                  {plan.run_state_display}
                </a>
              ) : (
                plan.run_state_display || '-'
              )}
            </div>
          </div>
        </div>

        {/* Actions & Commands side by side */}
        <div className={styles.commandsActions}>
          <div className={styles.actions}>
            <div className={styles.label}>Actions</div>
            <ActionButton
              label="Submit to Queue"
              actionKey="submit"
              status={actionStatuses['submit']}
              disabled={isMerged}
              onClick={() => executeAction('submit')}
            />
            <ActionButton
              label="Address PR Remote"
              actionKey="address-remote"
              status={actionStatuses['address-remote']}
              disabled={!hasPR || isMerged || !hasComments}
              onClick={() => executeAction('address-remote')}
            />
            <ActionButton
              label="Fix Conflicts Remote"
              actionKey="fix-conflicts"
              status={actionStatuses['fix-conflicts']}
              disabled={!hasPR || isMerged}
              onClick={() => executeAction('fix-conflicts')}
            />
            <ActionButton
              label="Land PR"
              actionKey="land"
              status={actionStatuses['land']}
              disabled={!hasPR || isMerged}
              onClick={() => executeAction('land')}
            />
            <ActionButton
              label="Close Plan"
              actionKey="close"
              status={actionStatuses['close']}
              disabled={isMerged}
              onClick={() => executeAction('close')}
            />
          </div>

          <div className={styles.copySection}>
            <div className={styles.label}>Commands</div>
            <div className={styles.copyCol}>
              {hasPR && <CodeSnippet code={`erk pr co ${plan.pr_number}`} onCopy={showToast} />}
              <CodeSnippet code={`erk prepare ${plan.issue_number}`} onCopy={showToast} />
              <CodeSnippet
                code={`source "$(erk prepare ${plan.issue_number} --script)" && erk implement --dangerous`}
                onCopy={showToast}
              />
              <CodeSnippet code={`erk plan submit ${plan.issue_number}`} onCopy={showToast} />
            </div>
            {toast && <div className={styles.toast}>{toast}</div>}
          </div>
        </div>
      </div>
    </Box>
  );
}

function ActionButton({
  label,
  status,
  disabled,
  onClick,
}: {
  label: string;
  actionKey: string;
  status?: ActionStatus;
  disabled: boolean;
  onClick: () => void;
}) {
  const isRunning = status?.state === 'running';

  return (
    <div className={styles.actionItem}>
      <Button
        intent={
          status?.state === 'success' ? 'success' : status?.state === 'error' ? 'danger' : 'primary'
        }
        disabled={disabled || isRunning}
        onClick={onClick}
        style={{width: '100%'}}
      >
        {isRunning ? `${label}...` : label}
      </Button>
      {status?.state === 'error' && status.message && (
        <div className={styles.actionErrorMsg}>{status.message}</div>
      )}
      {status?.state === 'success' && status.message && (
        <div className={styles.actionSuccessMsg}>{status.message}</div>
      )}
    </div>
  );
}

function CodeSnippet({code, onCopy}: {code: string; onCopy: (msg: string) => void}) {
  return (
    <button className={styles.codeSnippet} onClick={() => copyToClipboard(code, onCopy)}>
      <code>{code}</code>
    </button>
  );
}
