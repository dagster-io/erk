import {useState} from 'react';

interface SetupRequirementsProps {
  setupInstructions?: string[];
  connectionPermissions?: {
    header: string;
    permissions: string[];
  };
  networkInfo?: {
    connectionMethod: string;
    port?: string;
    ipAddresses?: string[];
    additionalInfo?: string;
  };
}

export default function SetupRequirements({
  setupInstructions,
  connectionPermissions,
  networkInfo,
}: SetupRequirementsProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Don't render if no content provided
  if (!setupInstructions && !connectionPermissions && !networkInfo) {
    return null;
  }

  return (
    <div className="bg-[#468AFC]/10 border border-[#468AFC]/20 rounded-lg mb-8">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full p-6 text-left focus:outline-none focus:ring-2 focus:ring-[#468AFC] focus:ring-inset rounded-lg"
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <svg className="w-5 h-5 text-gray-500 mr-3" fill="currentColor" viewBox="0 0 256 256">
              <path d="M108,84a16,16,0,1,1,16,16A16,16,0,0,1,108,84Zm128,44A108,108,0,1,1,128,20,108.12,108.12,0,0,1,236,128Zm-24,0a84,84,0,1,0-84,84A84.09,84.09,0,0,0,212,128Zm-72,36.68V132a20,20,0,0,0-20-20,12,12,0,0,0-4,23.32V168a20,20,0,0,0,20,20,12,12,0,0,0,4-23.32Z" />
            </svg>
            <h3 className="text-base font-medium text-gray-700">Setup Requirements</h3>
          </div>
          <div className="flex items-center text-[#3C39EE]">
            <span className="text-sm">{isExpanded ? 'Collapse' : 'Expand'}</span>
            <svg
              className={`w-5 h-5 ml-1 transform transition-transform ${isExpanded ? 'rotate-180' : ''}`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </div>
        </div>
      </button>

      {isExpanded && (
        <div className="border-t border-[#468AFC]/20 p-6">
          {setupInstructions && (
            <div className="mb-6">
              <h4 className="text-base font-medium text-gray-900 mb-3">Setup Instructions</h4>
              <ul className="space-y-2">
                {setupInstructions.map((instruction, index) => (
                  <li key={index} className="flex items-center">
                    <span className="text-light-blue-brand mr-2">•</span>
                    <span className="text-sm text-gray-700">{instruction}</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {connectionPermissions && (
            <div className="mb-6">
              <h4 className="text-base font-medium text-gray-900 mb-3">
                {connectionPermissions.header}
              </h4>
              <ul className="space-y-2">
                {connectionPermissions.permissions.map((permission, index) => (
                  <li key={index} className="flex items-center">
                    <span className="text-light-blue-brand mr-2">•</span>
                    <code className="text-sm bg-gray-100 px-2 py-1 rounded text-gray-800">
                      {permission}
                    </code>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {networkInfo && (
            <div>
              <h4 className="text-base font-medium text-gray-900 mb-3">Network Information</h4>
              <div className="bg-gray-50 rounded-lg p-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                  <div>
                    <span className="font-medium text-gray-700">Connection Method:</span>
                    <span className="text-gray-600 ml-2">{networkInfo.connectionMethod}</span>
                  </div>
                  {networkInfo.port && (
                    <div>
                      <span className="font-medium text-gray-700">Port:</span>
                      <span className="text-gray-600 ml-2">{networkInfo.port}</span>
                    </div>
                  )}
                </div>
                {networkInfo.ipAddresses && networkInfo.ipAddresses.length > 0 && (
                  <div className="mt-3">
                    <span className="font-medium text-gray-700">IP Addresses:</span>
                    <div className="mt-2 flex flex-wrap gap-2">
                      {networkInfo.ipAddresses.map((ip, index) => (
                        <code key={index} className="text-xs bg-white px-2 py-1 rounded border">
                          {ip}
                        </code>
                      ))}
                    </div>
                  </div>
                )}
                {networkInfo.additionalInfo && (
                  <div className="mt-3 text-sm text-gray-600">{networkInfo.additionalInfo}</div>
                )}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
