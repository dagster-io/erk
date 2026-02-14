import {useCallback, useEffect, useState} from 'react';

import type {LocalPlanDetail, LocalPlanFile} from '../../shared/types.js';

const POLL_INTERVAL = 15_000;

export function useLocalPlansList() {
  const [plans, setPlans] = useState<LocalPlanFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchPlans = useCallback(async () => {
    try {
      const res = await fetch('/api/local-plans');
      const data = await res.json();
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

  return {plans, loading, error};
}

export function useLocalPlanDetail(slug: string | null) {
  const [plan, setPlan] = useState<LocalPlanDetail | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (slug === null) {
      setPlan(null);
      setError(null);
      return;
    }

    setLoading(true);
    fetch(`/api/local-plans/${encodeURIComponent(slug)}`)
      .then((res) => res.json())
      .then((data) => {
        if (data.success) {
          setPlan(data.plan);
          setError(null);
        } else {
          setError(data.error ?? 'Unknown error');
        }
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : 'Fetch failed');
      })
      .finally(() => {
        setLoading(false);
      });
  }, [slug]);

  return {plan, loading, error};
}
