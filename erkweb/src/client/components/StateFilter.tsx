import {PLAN_STATES, type PlanState} from '../../shared/types.js';
import './StateFilter.css';

interface StateFilterProps {
  selectedState: PlanState | null;
  counts: Record<PlanState, number>;
  onSelect: (state: PlanState | null) => void;
}

export function StateFilter({selectedState, counts, onSelect}: StateFilterProps) {
  const total = Object.values(counts).reduce((sum, n) => sum + n, 0);

  return (
    <div className="state-filter">
      <div className="state-filter-list">
        <div
          className={`state-filter-item ${selectedState === null ? 'selected' : ''}`}
          onClick={() => onSelect(null)}
        >
          <span className="state-filter-label">All</span>
          <span className="state-filter-count">{total}</span>
        </div>
        {PLAN_STATES.map((state) => (
          <div
            key={state.key}
            className={`state-filter-item ${selectedState === state.key ? 'selected' : ''} ${counts[state.key] === 0 ? 'empty' : ''}`}
            onClick={() => onSelect(selectedState === state.key ? null : state.key)}
          >
            <span className="state-filter-label">{state.label}</span>
            <span className="state-filter-count">{counts[state.key]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
