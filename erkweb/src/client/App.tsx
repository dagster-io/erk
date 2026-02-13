import {useMemo, useState} from 'react';

import {PlanDetail} from './components/PlanDetail.js';
import {PlanSidebar} from './components/PlanSidebar.js';
import {StateFilter} from './components/StateFilter.js';
import {usePlans} from './hooks/usePlans.js';
import {PLAN_STATES, type PlanRow, type PlanState, derivePlanState} from '../shared/types.js';
import './App.css';

export function App() {
  const {plans, loading, error} = usePlans();
  const [selectedPlan, setSelectedPlan] = useState<PlanRow | null>(null);
  const [selectedState, setSelectedState] = useState<PlanState | null>(null);

  const stateCounts = useMemo(() => {
    const counts = Object.fromEntries(PLAN_STATES.map((s) => [s.key, 0])) as Record<
      PlanState,
      number
    >;
    for (const plan of plans) {
      const state = derivePlanState(plan);
      counts[state]++;
    }
    return counts;
  }, [plans]);

  const filteredPlans = useMemo(() => {
    if (selectedState === null) {
      return plans;
    }
    return plans.filter((plan) => derivePlanState(plan) === selectedState);
  }, [plans, selectedState]);

  return (
    <div className="app">
      <StateFilter selectedState={selectedState} counts={stateCounts} onSelect={setSelectedState} />
      <PlanSidebar
        plans={filteredPlans}
        loading={loading}
        error={error}
        selectedPlan={selectedPlan}
        onSelect={setSelectedPlan}
      />
      <div className="main-content">
        {selectedPlan ? (
          <PlanDetail plan={selectedPlan} onClose={() => setSelectedPlan(null)} />
        ) : (
          <div className="empty-state">Select a plan to view details</div>
        )}
      </div>
    </div>
  );
}
