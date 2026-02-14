import {Box, Colors} from '@dagster-io/ui-components';

import styles from './StateFilter.module.css';
import {PLAN_STATES, type PlanState} from '../../shared/types.js';

interface StateFilterProps {
  selectedState: PlanState | null;
  counts: Record<PlanState, number>;
  onSelect: (state: PlanState | null) => void;
}

export function StateFilter({selectedState, counts, onSelect}: StateFilterProps) {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <Box
      flex={{direction: 'column'}}
      style={{height: '100%', overflow: 'hidden'}}
      background={Colors.backgroundDefault()}
    >
      <div className={styles.list}>
        <div
          className={`${styles.item} ${selectedState === null ? styles.selected : ''}`}
          onClick={() => onSelect(null)}
        >
          <span className={styles.label}>All</span>
          <span className={styles.count}>{total}</span>
        </div>
        {PLAN_STATES.map((state) => (
          <div
            key={state.key}
            className={`${styles.item} ${selectedState === state.key ? styles.selected : ''} ${counts[state.key] === 0 ? styles.empty : ''}`}
            onClick={() => onSelect(selectedState === state.key ? null : state.key)}
          >
            <span className={styles.label}>{state.label}</span>
            <span className={styles.count}>{counts[state.key]}</span>
          </div>
        ))}
      </div>
    </Box>
  );
}
