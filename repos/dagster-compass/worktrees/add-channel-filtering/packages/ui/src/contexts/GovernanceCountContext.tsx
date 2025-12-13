import {createContext, useContext} from 'react';

interface GovernanceCountContextType {
  count: number | null;
  loading: boolean;
  refresh: () => Promise<void>;
}

export const GovernanceCountContext = createContext<GovernanceCountContextType | undefined>(
  undefined,
);

export function useGovernanceCount() {
  const context = useContext(GovernanceCountContext);
  if (context === undefined) {
    throw new Error('useGovernanceCount must be used within a GovernanceCountProvider');
  }
  return context;
}
