import {useState} from 'react';
import {useNavigate, useSearchParams} from 'react-router-dom';
import {useDocumentTitle} from './hooks/useDocumentTitle';
import ChooseDataTypeOnboardingScreen from './ChooseDataTypeOnboardingScreen';

export default function ChooseDataSource() {
  useDocumentTitle('Choose Your Data Source - Compass');

  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const organization = searchParams.get('org') || 'Organization';
  const [isLoading, setIsLoading] = useState(false);

  const handleSelectProspectingData = () => {
    // Set flag to restore state and show data-types step
    sessionStorage.setItem('compass_returning_from_choose_data', 'true');
    // Navigate back to signup (will restore state and show data-types step)
    navigate('/signup');
  };

  const handleSelectOwnData = async () => {
    // Get stored email/org from sessionStorage
    const email = sessionStorage.getItem('compass_signup_email');
    const org = sessionStorage.getItem('compass_signup_org');

    if (!email || !org) {
      // If somehow missing, redirect to signup
      navigate('/signup');
      return;
    }

    setIsLoading(true);

    try {
      // Call minimal onboarding API (creates Slack team, Stripe, org)
      // This is a one-way operation - creates resources that can't be easily undone
      const response = await fetch('/api/onboarding/process', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          email,
          organization: org,
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || 'Failed to start onboarding');
      }

      // Clear sessionStorage after successful minimal onboarding to prevent:
      // 1. User hitting back button and switching to curated data (would create duplicate orgs)
      // 2. Accidental re-submission
      // At this point, Slack team + Stripe subscription have been created
      sessionStorage.removeItem('compass_signup_email');
      sessionStorage.removeItem('compass_signup_org');
      sessionStorage.removeItem('compass_returning_from_choose_data');

      // Redirect to connections page (JWT cookie is set by backend for auth)
      window.location.href = data.redirect_url || '/onboarding/connections';
    } catch (err) {
      console.error('Error during onboarding:', err);
      // TODO: Show error to user
      setIsLoading(false);
    }
  };

  // Show loading screen while setting up
  if (isLoading) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen py-8 px-4">
        <div className="max-w-2xl text-center">
          <h1 className="text-2xl font-semibold text-gray-900 mb-4">Setting up your workspace</h1>
          <div className="bg-gray-50 border border-gray-200 rounded-lg p-6 mb-6">
            <div className="flex items-center justify-center gap-3 mb-4">
              <div className="animate-spin h-5 w-5 border-2 border-blue-brand border-t-transparent rounded-full"></div>
              <p className="text-base text-gray-700 font-medium">
                Creating your Slack workspace and setting up your account...
              </p>
            </div>
            <p className="text-sm text-gray-600">This may take a moment.</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <ChooseDataTypeOnboardingScreen
      organization={organization}
      onSelectProspectingData={handleSelectProspectingData}
      onSelectOwnData={handleSelectOwnData}
    />
  );
}
