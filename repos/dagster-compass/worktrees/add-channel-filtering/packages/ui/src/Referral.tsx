import {useState} from 'react';

interface ReferralLinkResponse {
  success: boolean;
  onboarding_link?: string;
  error?: string;
}

interface LogCopyReferralLinkResponse {
  success: boolean;
  error?: string;
}

export default function Referral() {
  const [isGenerating, setIsGenerating] = useState(false);
  const [referralLink, setReferralLink] = useState<string>('');
  const [showCopySuccess, setShowCopySuccess] = useState(false);
  const [error, setError] = useState<string>('');

  const handleGenerateReferral = async () => {
    setIsGenerating(true);
    setError('');

    try {
      const response = await fetch('/api/referral/generate-referral-token', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      const data: ReferralLinkResponse = await response.json();

      if (data.success && data.onboarding_link) {
        setReferralLink(data.onboarding_link);
      } else {
        setError(data.error || 'Failed to generate referral link');
        setIsGenerating(false);
      }
    } catch (err) {
      console.error('Generate referral link error:', err);
      setError('Network error while generating referral link');
      setIsGenerating(false);
    }
  };

  const handleCopyLink = async () => {
    try {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        await navigator.clipboard.writeText(referralLink);
        setShowCopySuccess(true);
        setTimeout(() => setShowCopySuccess(false), 3000);
      } else {
        // Fallback for older browsers
        const input = document.getElementById('referral-link-input') as HTMLInputElement;
        if (input) {
          input.select();
          const successful = document.execCommand('copy');
          if (successful) {
            setShowCopySuccess(true);
            setTimeout(() => setShowCopySuccess(false), 3000);
          } else {
            setError('Failed to copy to clipboard');
          }
        }
      }
      try {
        const response = await fetch('/api/referral/log-copy-referral-link', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        const data: LogCopyReferralLinkResponse = await response.json();

        if (data.success) {
          console.log('Copy referral link action successfully logged.');
        }
      } catch (err) {
        console.error('Log copy referral link error:', err);
      }
    } catch (err) {
      console.error('Failed to copy: ', err);
      setError('Failed to copy to clipboard');
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-8 py-8">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-gray-900">Referral Link</h1>
      </div>

      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="space-y-4">
          <p className="text-sm text-gray-600">
            Share your unique referral link to invite others to join Compass.
            <span className="font-semibold text-blue-600"> You'll earn +100 bonus answers</span> for
            each successful referral, and{' '}
            <span className="font-semibold text-green-600">they'll receive +50 bonus answers</span>{' '}
            when they sign up!
          </p>

          {error && (
            <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">{error}</p>
            </div>
          )}

          {!referralLink ? (
            <div>
              <button
                onClick={handleGenerateReferral}
                disabled={isGenerating}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed"
              >
                {isGenerating ? 'Generating...' : 'Generate Referral Link'}
              </button>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  id="referral-link-input"
                  value={referralLink}
                  readOnly
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm bg-gray-50 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
                <button
                  onClick={handleCopyLink}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors whitespace-nowrap"
                >
                  Copy Link
                </button>
              </div>
              {showCopySuccess && (
                <p className="text-sm text-green-600">✓ Link copied to clipboard!</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
