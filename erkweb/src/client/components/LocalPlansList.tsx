import {Box, Colors, NonIdealState, SpinnerWithText, Tag} from '@dagster-io/ui-components';

import styles from './LocalPlansList.module.css';
import type {LocalPlanFile} from '../../shared/types.js';

interface LocalPlansListProps {
  plans: LocalPlanFile[];
  loading: boolean;
  error: string | null;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
}

function formatRelativeTime(ms: number): string {
  const seconds = Math.floor((Date.now() - ms) / 1000);
  if (seconds < 60) {
    return 'just now';
  }
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) {
    return `${minutes}m ago`;
  }
  const hours = Math.floor(minutes / 60);
  if (hours < 24) {
    return `${hours}h ago`;
  }
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function LocalPlansList({
  plans,
  loading,
  error,
  selectedSlug,
  onSelect,
}: LocalPlansListProps) {
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
        <span style={{fontWeight: 700, fontSize: 14, lineHeight: '20px'}}>Local Plans</span>
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
          <NonIdealState icon="search" title="No local plans found" />
        )}
        {!loading &&
          !error &&
          plans.map((plan) => (
            <div
              key={plan.slug}
              className={`${styles.item} ${selectedSlug === plan.slug ? styles.selected : ''}`}
              onClick={() => onSelect(plan.slug)}
            >
              <div className={styles.primary}>
                <span className={styles.title}>{plan.title}</span>
              </div>
              <div className={styles.meta}>
                {plan.commentCount > 0 ? (
                  <span className={styles.comments}>
                    {plan.commentCount} comment{plan.commentCount !== 1 ? 's' : ''}
                  </span>
                ) : (
                  <span className={styles.noComments}>No comments</span>
                )}
                <span className={styles.time}>{formatRelativeTime(plan.modifiedAt)}</span>
              </div>
            </div>
          ))}
      </div>
    </Box>
  );
}
