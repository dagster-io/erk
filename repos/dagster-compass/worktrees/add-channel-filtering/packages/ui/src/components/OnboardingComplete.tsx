interface OnboardingCompleteProps {
  subtitle?: string;
  channelName?: string;
  error?: string | null;
}

export function OnboardingComplete({
  subtitle = 'Accept the invite to start chatting with your data',
  channelName,
  error,
}: OnboardingCompleteProps) {
  return (
    <>
      {/* Email CTA Section */}
      <div className="bg-white rounded-lg p-6 border border-gray-200 shadow-sm mb-6">
        <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">Check your email</h2>

        {/* Envelope icon */}
        <div className="flex justify-center mb-4">
          <i
            className="ph-duotone ph-envelope-open light-blue-brand"
            style={{fontSize: '200px'}}
          ></i>
        </div>

        {/* Bold confirmation */}
        <p className="text-center text-xl text-gray-900 mb-8">
          {"We've sent a Slack Connect invite to your email"}
          <br />
          <span className="text-base text-gray-600 mt-2 block">{subtitle}</span>
        </p>
      </div>

      {/* Next Steps */}
      <div className="max-w-md mx-auto">
        <h2 className="text-2xl font-semibold text-gray-900 mb-6 text-center">Next steps</h2>

        <ol className="space-y-4 text-left">
          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-gray-300 text-sm font-medium">
              1
            </span>
            <div>
              <p className="text-base font-semibold text-gray-900">Accept the invite</p>
              <p className="text-gray-600 mt-1">
                Open the email and accept the Slack Connect request. It might take a few minutes for
                the email to arrive.
              </p>
            </div>
          </li>

          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-gray-300 text-sm font-medium">
              2
            </span>
            <div>
              <p className="text-base font-semibold text-gray-900">{"You'll be added to Slack"}</p>
              <p className="text-gray-600 mt-1">
                {"We'll automatically add you to your Compass channel."}
              </p>
            </div>
          </li>

          <li className="flex gap-3">
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-gray-300 text-sm font-medium">
              3
            </span>
            <div>
              <p className="text-base font-semibold text-gray-900">Start asking questions</p>
              <p className="text-gray-600 mt-1">
                {channelName
                  ? `Compass will be ready to help you analyze your data in #${channelName}.`
                  : 'Ask Compass about your data by @mentioning it in your channel.'}
              </p>
            </div>
          </li>
        </ol>
      </div>

      {error && (
        <div className="mt-6 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-red-800">{error}</p>
        </div>
      )}
    </>
  );
}
