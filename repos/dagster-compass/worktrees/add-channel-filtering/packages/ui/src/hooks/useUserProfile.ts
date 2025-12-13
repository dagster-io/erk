import {useEffect, useRef, useState} from 'react';
import {UserProfile} from '../types/user';
import {fetchWithAuth} from '../utils/authErrors';

export function useUserProfile() {
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
        const response = await fetchWithAuth('/api/user/profile', {
          credentials: 'include',
        });

        const data = await response.json();

        if (data.error) {
          setError(data.error);
          setProfile({user_id: data.user_id || 'unknown', display_name: 'User', ...data});
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

  return {profile, loading, error};
}
