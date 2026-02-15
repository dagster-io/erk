import {Box, Colors, NonIdealState, SpinnerWithText, Tag} from '@dagster-io/ui-components';

import styles from './PlanSidebar.module.css';
import type {PlanRow} from '../../shared/types.js';

interface PlanSidebarProps {
  plans: PlanRow[];
  loading: boolean;
  error: string | null;
  selectedPlan: PlanRow | null;
  onSelect: (plan: PlanRow) => void;
}

export function PlanSidebar({plans, loading, error, selectedPlan, onSelect}: PlanSidebarProps) {
  return (
    <Box
      flex={{direction: 'column'}}
      style={{height: '100%', overflow: 'hidden'}}
      background={Colors.backgroundLight()}
      border="right"
    >
      <Box
        flex={{direction: 'row', gap: 8, alignItems: 'center'}}
        padding={{horizontal: 12, vertical: 8}}
        background={Colors.backgroundLighterHover()}
        border="bottom"
        style={{flexShrink: 0}}
      >
        <span style={{fontWeight: 700, fontSize: 14, lineHeight: '20px'}}>Plans</span>
        <Tag>{plans.length}</Tag>
      </Box>
      <div className={styles.content}>
        {loading && (
          <div className={styles.status}>
            <SpinnerWithText label="Loading..." />
          </div>
        )}
        {error && <NonIdealState icon="error" title="Error" description={error} />}
        {!loading && !error && plans.length === 0 && (
          <NonIdealState icon="search" title="No plans found" />
        )}
        {!loading &&
          !error &&
          plans.map((plan) => (
            <div
              key={plan.issue_number}
              className={`${styles.item} ${selectedPlan?.issue_number === plan.issue_number ? styles.selected : ''}`}
              onClick={() => onSelect(plan)}
            >
              <div className={styles.primary}>
                <span className={styles.number}>#{plan.issue_number}</span>
                <span className={styles.title}>{plan.title}</span>
              </div>
              <div className={styles.meta}>
                <span className={styles.metaTag}>
                  impl:{' '}
                  <span className={styles.metaValue}>{plan.local_impl_display || 'none'}</span>
                </span>
                <span className={styles.metaTag}>
                  pr: <span className={styles.metaValue}>{plan.pr_display || 'none'}</span>
                </span>
                <span className={styles.metaTag}>
                  checks: <span className={styles.metaValue}>{plan.checks_display || 'none'}</span>
                </span>
                <span className={styles.metaTag}>
                  run: <span className={styles.metaValue}>{plan.run_state_display || 'none'}</span>
                </span>
              </div>
            </div>
          ))}
      </div>
    </Box>
  );
}
