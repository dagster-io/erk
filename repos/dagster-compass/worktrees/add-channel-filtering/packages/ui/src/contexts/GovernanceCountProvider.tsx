import {ReactNode, useState, useCallback, useEffect} from 'react';
import {fetchWithAuth} from '../utils/authErrors';
import {GovernanceCountContext} from './GovernanceCountContext';

export function GovernanceCountProvider({children}: {children: ReactNode}) {
  const [count, setCount] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchCount = useCallback(async () => {
    try {
      const response = await fetchWithAuth('/api/context-governance/list?status=OPEN');
      const result = await response.json();
      // Exclude DATA_REQUEST entries from the count
      const filteredCount =
        result.entries?.filter(
          (entry: {update_type: string}) => entry.update_type !== 'DATA_REQUEST',
        ).length ?? 0;
      setCount(filteredCount);
    } catch (err) {
      console.error('Failed to fetch governance count:', err);
      setCount(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    fetchCount();

    // Poll every 60 seconds
    const interval = setInterval(fetchCount, 60000);

    return () => clearInterval(interval);
  }, [fetchCount]);

  return (
    <GovernanceCountContext.Provider value={{count, loading, refresh: fetchCount}}>
      {children}
    </GovernanceCountContext.Provider>
  );
}
