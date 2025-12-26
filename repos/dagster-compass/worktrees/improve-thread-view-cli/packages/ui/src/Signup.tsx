import {useState, FormEvent, ChangeEvent} from 'react';
import {useDocumentTitle} from './hooks/useDocumentTitle';
import {MarketingLayout} from './layouts/MarketingLayout';
import ChooseDataTypeOnboardingScreen from './ChooseDataTypeOnboardingScreen';
import {HelpFooter} from './components/HelpFooter';
import {OnboardingComplete} from './components/OnboardingComplete';

interface SignupState {
  step:
    | 'email-org'
    | 'choose-data-source'
    | 'prospect-data-types'
    | 'byow-loading'
    | 'prospector-complete';
  email: string;
  organization: string;
  dataTypes: string[];
  terms: boolean;
  isSubmitting: boolean;
  error: string | null;
}

const DATA_TYPES = [
  {value: 'sales', label: 'Sales'},
  {value: 'recruiting', label: 'Recruiting'},
  {value: 'investing', label: 'Investing'},
];

interface FormErrors {
  email: string;
  organization: string;
  terms: string;
  dataTypes: string;
}

function Signup() {
  useDocumentTitle('Welcome to Compass');

  const [state, setState] = useState<SignupState>({
    step: 'email-org',
    email: '',
    organization: '',
    dataTypes: [],
    terms: false,
    isSubmitting: false,
    error: null,
  });

  const [errors, setErrors] = useState<FormErrors>({
    email: '',
    organization: '',
    terms: '',
    dataTypes: '',
  });

  // Email validation regex matching onboarding
  const emailRegex =
    /^[a-zA-Z0-9]([a-zA-Z0-9._%+-]*[a-zA-Z0-9])?@[a-zA-Z0-9]([a-zA-Z0-9.-]*[a-zA-Z0-9])?\.[a-zA-Z]{2,}$/;

  const showError = (field: keyof FormErrors, message: string) => {
    setErrors((prev) => ({...prev, [field]: message}));
  };

  const hideError = (field: keyof FormErrors) => {
    setErrors((prev) => ({...prev, [field]: ''}));
  };

  const validateEmail = (): boolean => {
    const emailValue = state.email.trim();
    if (!emailValue) {
      showError('email', 'Email is required');
      return false;
    }
    if (!emailRegex.test(emailValue)) {
      showError('email', 'Please enter a valid email address');
      return false;
    }
    hideError('email');
    return true;
  };

  const validateOrganization = (): boolean => {
    const orgValue = state.organization.trim();
    if (!orgValue) {
      showError('organization', 'Organization name is required');
      return false;
    }
    if (orgValue.length < 2) {
      showError('organization', 'Organization name must be at least 2 characters');
      return false;
    }
    hideError('organization');
    return true;
  };

  const validateTerms = (): boolean => {
    if (!state.terms) {
      showError('terms', 'You must agree to the Terms of Service and Privacy Policy');
      return false;
    }
    hideError('terms');
    return true;
  };

  const validateDataTypes = (): boolean => {
    if (state.dataTypes.length === 0) {
      showError('dataTypes', 'Please select at least one data type');
      return false;
    }
    hideError('dataTypes');
    return true;
  };

  const handleInputChange = (e: ChangeEvent<HTMLInputElement>) => {
    const {name, value, type, checked} = e.target;
    setState((prev) => ({
      ...prev,
      [name]: type === 'checkbox' ? checked : value,
    }));
    // Clear errors on input
    if (name in errors) {
      hideError(name as keyof FormErrors);
    }
  };

  const handleDataTypeChange = (e: ChangeEvent<HTMLInputElement>) => {
    const {value, checked} = e.target;
    setState((prev) => {
      const newDataTypes = checked
        ? [...prev.dataTypes, value]
        : prev.dataTypes.filter((type) => type !== value);
      return {...prev, dataTypes: newDataTypes};
    });
    hideError('dataTypes');
  };

  const handleBlur = (field: 'email' | 'organization') => {
    if (field === 'email') {
      validateEmail();
    } else if (field === 'organization') {
      validateOrganization();
    }
  };

  const handleSelectProspectingData = () => {
    // User chose prospecting data - show data type selection
    setState((prev) => ({...prev, step: 'prospect-data-types'}));
  };

  const handleSelectOwnData = () => {
    // User chose own data - redirect to connections page (JWT already set during minimal onboarding)
    window.location.href = '/onboarding/connections';
  };

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setState((prev) => ({...prev, error: null}));

    if (state.step === 'email-org') {
      // Validate step 1 fields
      const isEmailValid = validateEmail();
      const isOrganizationValid = validateOrganization();
      const isTermsValid = validateTerms();

      if (isEmailValid && isOrganizationValid && isTermsValid) {
        // Call minimal onboarding first (creates Slack team, Stripe, org, contextstore)
        setState((prev) => ({...prev, step: 'byow-loading', isSubmitting: true}));

        try {
          const response = await fetch('/api/onboarding/process', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include', // Required for cookies to be set
            body: JSON.stringify({
              email: state.email,
              organization: state.organization,
            }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error || 'Failed to start onboarding');
          }

          // Minimal onboarding complete, JWT cookie is set - now show data source choice
          setState((prev) => ({...prev, step: 'choose-data-source', isSubmitting: false}));
        } catch (err) {
          console.error('Error during onboarding:', err);
          setState((prev) => ({
            ...prev,
            error: 'Failed to set up workspace. Please try again.',
            isSubmitting: false,
            step: 'email-org',
          }));
        }
      }
    } else if (state.step === 'prospect-data-types') {
      // Validate step 2 fields
      const isDataTypesValid = validateDataTypes();

      if (isDataTypesValid) {
        // Complete prospector setup (channels + bot + connection + slack connect)
        setState((prev) => ({...prev, isSubmitting: true}));

        try {
          const response = await fetch('/api/onboarding/prospector/complete', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            credentials: 'include', // Required to send cookies
            body: JSON.stringify({
              dataTypes: state.dataTypes,
            }),
          });

          const data = await response.json();

          if (!response.ok) {
            throw new Error(data.error || 'Failed to complete prospector setup');
          }

          // Show success page
          setState((prev) => ({...prev, step: 'prospector-complete', isSubmitting: false}));
        } catch (err) {
          console.error('Error completing prospector setup:', err);
          setState((prev) => ({
            ...prev,
            error: 'Failed to complete setup. Please try again.',
            isSubmitting: false,
          }));
        }
      }
    }
  };

  const getHeaderText = () => {
    if (state.step === 'email-org') {
      return 'Welcome to Compass';
    }
    if (state.step === 'choose-data-source') {
      return '';
    } // No header for cards page
    if (state.step === 'prospect-data-types') {
      return 'What type of prospecting data would you like to use?';
    }
    return '';
  };

  return (
    <>
      {state.step === 'email-org' && (
        <MarketingLayout>
          {/* Logo */}
          <div className="mb-6 flex justify-center">
            <img src="/static/compass-logo-mark.svg" alt="Compass Logo" className="h-32 w-auto" />
          </div>

          {/* Header */}
          <div className="text-center mb-8">
            <h2 className="header-text text-4xl">{getHeaderText()}</h2>
            <p className="mt-4 text-lg text-gray-600 subheader-text max-w-sm mx-auto">
              Get started by signing in with the email you use for your team's Slack.
            </p>
            <div className="text-sm text-gray-500 mx-auto mt-2 flex items-center justify-center gap-1">
              <i className="ph-bold ph-info text-gray-500 text-sm"></i>
              <span>
                Slack Connect may require admin approval.{' '}
                <a
                  href="http://docs.compass.dagster.io/admins/slack-admin-setup"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="blue-brand hover:text-blue-brand-dark hover:underline"
                >
                  Learn more ↗
                </a>
              </span>
            </div>
          </div>

          {/* Form Container */}
          <div className="w-full max-w-md mx-auto bg-white rounded-2xl border border-gray-200 shadow-xl p-8 transition-all duration-300 hover:shadow-2xl mt-4">
            <form onSubmit={handleSubmit} className="space-y-6" noValidate>
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-2">
                  Email
                </label>
                <input
                  type="email"
                  id="email"
                  name="email"
                  value={state.email}
                  onChange={handleInputChange}
                  onBlur={() => handleBlur('email')}
                  className={`mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border ${
                    errors.email
                      ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 focus:ring-blue-brand focus:border-blue-brand'
                  } placeholder-gray-400 text-gray-900 focus:outline-none focus:z-10 sm:text-md`}
                  placeholder="jane@acmecorp.com"
                />
                {errors.email && <div className="mt-1 text-sm text-red-600">{errors.email}</div>}
              </div>

              <div>
                <label
                  htmlFor="organization"
                  className="block text-sm font-medium text-gray-700 mb-2"
                >
                  Organization name
                </label>
                <input
                  type="text"
                  id="organization"
                  name="organization"
                  value={state.organization}
                  onChange={handleInputChange}
                  onBlur={() => handleBlur('organization')}
                  className={`mt-1 appearance-none rounded-md relative block w-full px-3 py-2 border ${
                    errors.organization
                      ? 'border-red-300 focus:ring-red-500 focus:border-red-500'
                      : 'border-gray-300 focus:ring-blue-brand focus:border-blue-brand'
                  } placeholder-gray-400 text-gray-900 focus:outline-none focus:z-10 sm:text-md`}
                  placeholder="Acme Corp"
                />
                {errors.organization && (
                  <div className="mt-1 text-sm text-red-600">{errors.organization}</div>
                )}
              </div>

              <div>
                <div className="flex items-start">
                  <input
                    id="terms"
                    name="terms"
                    type="checkbox"
                    checked={state.terms}
                    onChange={handleInputChange}
                    className={`h-4 w-4 mt-0.5 text-blue-brand focus:ring-blue-brand border-gray-300 rounded ${
                      errors.terms ? 'border-red-500' : ''
                    }`}
                  />
                  <label htmlFor="terms" className="ml-2 block text-sm text-gray-700">
                    I agree to the{' '}
                    <a
                      href="https://dagster.io/privacy"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-brand hover:text-blue-brand-dark underline"
                    >
                      Privacy Policy
                    </a>{' '}
                    and{' '}
                    <a
                      href="https://compass.dagster.io/terms"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-brand hover:text-blue-brand-dark underline"
                    >
                      Terms of Service
                    </a>
                  </label>
                </div>
                {errors.terms && (
                  <div className="mt-1 ml-6 text-sm text-red-600">{errors.terms}</div>
                )}
              </div>

              <button
                type="submit"
                className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-md font-medium rounded-md text-white bg-blue-brand hover:bg-blue-brand-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-brand disabled:opacity-50 disabled:cursor-not-allowed items-center"
              >
                Create account
              </button>
            </form>
          </div>

          {/* Help Text */}
          <HelpFooter showTermsLink={false} />
        </MarketingLayout>
      )}

      {state.step === 'choose-data-source' && (
        <ChooseDataTypeOnboardingScreen
          organization={state.organization}
          onSelectProspectingData={handleSelectProspectingData}
          onSelectOwnData={handleSelectOwnData}
        />
      )}

      {state.step === 'byow-loading' && (
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
            {state.error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800">{state.error}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {state.step === 'prospect-data-types' && (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center py-8 px-4">
          <div className="mt-24 w-full max-w-xl">
            {/* Header */}
            <div className="text-center mb-8">
              <h2 className="header-text text-4xl">{getHeaderText()}</h2>
            </div>

            {/* Form Container */}
            <div className="w-full bg-white rounded-2xl border border-gray-200 shadow-xl p-8 transition-all duration-300 hover:shadow-2xl">
              <form onSubmit={handleSubmit} className="space-y-6" noValidate>
                <div>
                  <label className="block text-md font-medium text-gray-700 mb-5">
                    Select at least one data type
                  </label>
                  <div className="space-y-3">
                    {DATA_TYPES.map((type) => (
                      <label
                        key={type.value}
                        className="flex items-center p-4 border border-gray-300 rounded-md cursor-pointer hover:bg-gray-50 transition-colors"
                      >
                        <input
                          type="checkbox"
                          name="data_types"
                          value={type.value}
                          checked={state.dataTypes.includes(type.value)}
                          onChange={handleDataTypeChange}
                          className="h-4 w-4 text-blue-brand focus:ring-blue-brand border-gray-300 rounded"
                        />
                        <span className="ml-3 text-sm text-gray-900">{type.label}</span>
                      </label>
                    ))}
                  </div>
                  {errors.dataTypes && (
                    <div className="mt-1 text-sm text-red-600">{errors.dataTypes}</div>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={state.isSubmitting}
                  className="group relative w-full flex justify-center py-2 px-4 border border-transparent text-md font-medium rounded-md text-white bg-blue-brand hover:bg-blue-brand-dark focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-brand disabled:opacity-50 disabled:cursor-not-allowed items-center gap-2"
                >
                  {state.isSubmitting && (
                    <div className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></div>
                  )}
                  <span id="submit-text">
                    {state.isSubmitting
                      ? 'Setting up your workspace...'
                      : 'Get started with Compass'}
                  </span>
                </button>
                <p className="mt-2 text-center">
                  <a
                    href="https://privacy.peopledatalabs.com/policies?name=services-subscription-agreement"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-brand hover:text-blue-brand-dark hover:underline text-sm "
                  >
                    Learn more about our data sources ↗
                  </a>
                </p>
              </form>
            </div>

            {state.error && (
              <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-red-800">{state.error}</p>
              </div>
            )}

            {/* Help Text */}
            <HelpFooter />
          </div>
        </div>
      )}

      {state.step === 'prospector-complete' && (
        <div className="min-h-screen bg-gray-50 flex flex-col items-center justify-center py-8 px-4">
          <div className="max-w-2xl w-full">
            {/* Setup Complete Banner */}
            <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-6">
              <div className="flex items-center justify-center gap-2">
                <i className="ph-fill ph-check-circle text-green-600 text-lg"></i>
                <p className="text-base text-green-700 font-medium">Setup complete!</p>
              </div>
            </div>

            <OnboardingComplete
              subtitle="Accept the invite to start exploring your prospecting data"
              error={state.error}
            />
          </div>
        </div>
      )}
    </>
  );
}

export default Signup;
