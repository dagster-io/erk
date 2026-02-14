import {useCallback, useEffect, useMemo, useState} from 'react';

import styles from './App.module.css';
import {LocalPlansList} from './components/LocalPlansList.js';
import {type AppMode, ModeToggle} from './components/ModeToggle.js';
import {PlanDetail} from './components/PlanDetail.js';
import {PlanReviewPanel} from './components/PlanReviewPanel.js';
import {PlanSidebar} from './components/PlanSidebar.js';
import {StateFilter} from './components/StateFilter.js';
import {useLocalPlanDetail, useLocalPlansList} from './hooks/useLocalPlans.js';
import {usePlans} from './hooks/usePlans.js';
import {PLAN_STATES, type PlanRow, type PlanState, derivePlanState} from '../shared/types.js';

const REVIEW_PREFIX = '/review-plans';

function parseRoute(): {mode: AppMode; slug: string | null} {
  const path = window.location.pathname;
  if (path === REVIEW_PREFIX || path.startsWith(REVIEW_PREFIX + '/')) {
    const slug = path.slice(REVIEW_PREFIX.length + 1) || null;
    return {mode: 'review', slug: slug ? decodeURIComponent(slug) : null};
  }
  return {mode: 'dashboard', slug: null};
}

export function App() {
  const initial = parseRoute();
  const [mode, setModeState] = useState<AppMode>(initial.mode);

  const setMode = useCallback((next: AppMode) => {
    setModeState(next);
    const path = next === 'review' ? REVIEW_PREFIX : '/dashboard';
    window.history.pushState(null, '', path);
  }, []);

  // Handle browser back/forward
  useEffect(() => {
    function handlePopState() {
      const route = parseRoute();
      setModeState(route.mode);
      setSelectedSlugState(route.slug);
    }
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Dashboard state
  const {plans, loading, error} = usePlans();
  const [selectedPlan, setSelectedPlan] = useState<PlanRow | null>(null);
  const [selectedState, setSelectedState] = useState<PlanState | null>(null);

  // Review state
  const {plans: localPlans, loading: localLoading, error: localError} = useLocalPlansList();
  const [selectedSlug, setSelectedSlugState] = useState<string | null>(initial.slug);
  const {plan: localPlanDetail} = useLocalPlanDetail(selectedSlug);

  const setSelectedSlug = useCallback((slug: string | null) => {
    setSelectedSlugState(slug);
    const path = slug ? `${REVIEW_PREFIX}/${encodeURIComponent(slug)}` : REVIEW_PREFIX;
    window.history.pushState(null, '', path);
  }, []);

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
    <div className={styles.appContainer}>
      <ModeToggle mode={mode} onModeChange={setMode} />
      {mode === 'dashboard' ? (
        <div className={styles.app}>
          <StateFilter
            selectedState={selectedState}
            counts={stateCounts}
            onSelect={setSelectedState}
          />
          <PlanSidebar
            plans={filteredPlans}
            loading={loading}
            error={error}
            selectedPlan={selectedPlan}
            onSelect={setSelectedPlan}
          />
          <div className={styles.mainContent}>
            {selectedPlan ? (
              <PlanDetail plan={selectedPlan} onClose={() => setSelectedPlan(null)} />
            ) : (
              <div className={styles.emptyState}>Select a plan to view details</div>
            )}
          </div>
        </div>
      ) : (
        <div className={styles.reviewLayout}>
          <LocalPlansList
            plans={localPlans}
            loading={localLoading}
            error={localError}
            selectedSlug={selectedSlug}
            onSelect={setSelectedSlug}
          />
          <div className={styles.mainContent}>
            {localPlanDetail ? (
              <PlanReviewPanel plan={localPlanDetail} />
            ) : (
              <div className={styles.emptyState}>Select a local plan to review</div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
