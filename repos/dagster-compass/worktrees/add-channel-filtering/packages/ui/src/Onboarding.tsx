import {useEffect} from 'react';
import {useSearchParams} from 'react-router-dom';

// Redirect /onboarding to /signup to consolidate onboarding flows
export default function Onboarding() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');

  useEffect(() => {
    // Preserve token parameter if present
    const signupUrl = token ? `/signup?token=${encodeURIComponent(token)}` : '/signup';
    window.location.href = signupUrl;
  }, [token]);

  return null;
}
