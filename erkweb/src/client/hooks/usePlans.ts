import {useCallback, useEffect, useState} from 'react';

import type {FetchPlansResult, PlanRow} from '../../shared/types.js';

const POLL_INTERVAL = 15_000;

export function usePlans() {
  const [plans, setPlans] = useState<PlanRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlans = useCallback(async () => {
    try {
      const res = await fetch('/api/plans');
      const data: FetchPlansResult = await res.json();
      if (data.success) {
        setPlans(data.plans);
        setError(null);
      } else {
        setError(data.error ?? 'Unknown error');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Fetch failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPlans();
    const interval = setInterval(fetchPlans, POLL_INTERVAL);
    return () => clearInterval(interval);
  }, [fetchPlans]);

  return {plans, loading, error, refetch: fetchPlans};
}
