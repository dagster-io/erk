import {createContext, useContext} from 'react';
import {UserProfile} from '../types/user';

interface UserProfileContextType {
  profile: UserProfile | null;
  loading: boolean;
  error: string | null;
}

export const UserProfileContext = createContext<UserProfileContextType | undefined>(undefined);

export function useUserProfile() {
  const context = useContext(UserProfileContext);
  if (context === undefined) {
    throw new Error('useUserProfile must be used within a UserProfileProvider');
  }
  return context;
}
