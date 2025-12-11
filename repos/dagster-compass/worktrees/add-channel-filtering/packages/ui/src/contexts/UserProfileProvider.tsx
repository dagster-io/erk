import {ReactNode, useState, useRef, useEffect} from 'react';
import {UserProfile} from '../types/user';
import {UserProfileContext} from './UserProfileContext';

export function UserProfileProvider({children}: {children: ReactNode}) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const hasFetched = useRef(false);

  useEffect(() => {
    if (hasFetched.current) {
      return;
    }

    hasFetched.current = true;

    async function fetchProfile() {
      try {
        const response = await fetch('/api/user/profile', {
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`Failed to fetch profile: ${response.statusText}`);
        }

        const data = await response.json();

        if (data.error) {
          console.log('Failure to fetch profile:', data.error);
          setError(data.error);
          setProfile(null);
        } else {
          setProfile(data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to fetch user profile');
        setProfile(null);
      } finally {
        setLoading(false);
      }
    }

    fetchProfile();
  }, []);

  return (
    <UserProfileContext.Provider value={{profile, loading, error}}>
      {children}
    </UserProfileContext.Provider>
  );
}
