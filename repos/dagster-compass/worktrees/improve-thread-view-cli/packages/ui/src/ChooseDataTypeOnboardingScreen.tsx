import {useState} from 'react';
import {PageHeader} from './components/PageHeader';
import {HelpFooter} from './components/HelpFooter';

interface ChooseDataTypeOnboardingScreenProps {
  organization: string;
  onSelectProspectingData: () => void;
  onSelectOwnData: () => void;
}

export default function ChooseDataTypeOnboardingScreen({
  organization,
  onSelectProspectingData,
  onSelectOwnData,
}: ChooseDataTypeOnboardingScreenProps) {
  const [isVideoExpanded, setIsVideoExpanded] = useState(false);

  return (
    <div className="flex flex-col items-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="mt-16 w-full max-w-4xl flex flex-col items-center">
        <h2 className="text-2xl font-semibold text-gray-900 mb-8">{organization}</h2>
        <PageHeader
          title="What type of data do you want to start with?"
          subtitle="Choose between our curated datasets or use your own data. You can always add more later."
          size="large"
        />

        {/* Collapsible video card */}
        <div className="w-full max-w-4xl mx-auto mb-8">
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm">
            <button
              onClick={() => setIsVideoExpanded(!isVideoExpanded)}
              className="w-full flex items-center justify-center p-4 hover:bg-gray-50 transition-colors relative"
            >
              <span className="text-base font-medium text-gray-900 text-center">
                🎬 Watch a video to get started
              </span>
              <svg
                className={`w-5 h-5 text-gray-500 transition-transform absolute right-4 ${isVideoExpanded ? 'rotate-180' : ''}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M19 9l-7 7-7-7"
                />
              </svg>
            </button>
            {isVideoExpanded && (
              <div className="px-4 pb-4">
                <div style={{position: 'relative', paddingBottom: '64.74820143884892%', height: 0}}>
                  <iframe
                    src="https://www.loom.com/embed/b354c4475e5d4714b9351b2a1230b785"
                    frameBorder="0"
                    allowFullScreen
                    style={{position: 'absolute', top: 0, left: 0, width: '100%', height: '100%'}}
                  />
                </div>
              </div>
            )}
          </div>
        </div>

        {/* White card wrapper - main content */}
        <div className="w-full max-w-4xl mx-auto bg-white rounded-2xl border border-gray-200 shadow-xl p-8 sm:p-6 transition-all duration-300 hover:shadow-2xl">
          {/* Data Source Selection Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Card 1: Curated prospecting data */}
            <button
              onClick={onSelectProspectingData}
              className="group bg-white border-2 border-gray-200 rounded-xl p-8 hover:border-[#3C39EE] hover:shadow-lg transition-all duration-200 text-left cursor-pointer"
            >
              <div className="flex flex-col items-start">
                <div className="w-16 h-16 mb-4 flex items-center justify-center bg-[#468AFC]/10 rounded-lg group-hover:bg-[#3C39EE]/10">
                  <svg
                    className="w-8 h-8 text-[#468AFC] group-hover:text-[#3C39EE]"
                    fill="currentColor"
                    viewBox="0 0 256 256"
                  >
                    <path d="M128,24h0A104,104,0,1,0,232,128,104.12,104.12,0,0,0,128,24Zm88,104a87.61,87.61,0,0,1-3.33,24H174.16a157.44,157.44,0,0,0,0-48h38.51A87.61,87.61,0,0,1,216,128ZM102,168H154a115.11,115.11,0,0,1-26,45A115.27,115.27,0,0,1,102,168Zm-3.9-16a140.84,140.84,0,0,1,0-48h59.88a140.84,140.84,0,0,1,0,48ZM40,128a87.61,87.61,0,0,1,3.33-24H81.84a157.44,157.44,0,0,0,0,48H43.33A87.61,87.61,0,0,1,40,128ZM154,88H102a115.11,115.11,0,0,1,26-45A115.27,115.27,0,0,1,154,88Zm52.33,0H170.71a135.28,135.28,0,0,0-22.3-45.6A88.29,88.29,0,0,1,206.37,88ZM107.59,42.4A135.28,135.28,0,0,0,85.29,88H49.63A88.29,88.29,0,0,1,107.59,42.4ZM49.63,168H85.29a135.28,135.28,0,0,0,22.3,45.6A88.29,88.29,0,0,1,49.63,168Zm98.78,45.6a135.28,135.28,0,0,0,22.3-45.6h35.66A88.29,88.29,0,0,1,148.41,213.6Z" />
                  </svg>
                </div>
                <h3 className="text-xl font-semibold text-gray-950 mb-2">
                  Curated prospecting data
                </h3>
                <p className="text-gray-600">
                  Ready-to-use datasets for sales, recruiting, or investing. No data connection
                  required.
                </p>
              </div>
            </button>

            {/* Card 2: Your own data */}
            <div
              onClick={onSelectOwnData}
              className="group bg-white border-2 border-gray-200 rounded-xl p-8 hover:border-[#3C39EE] hover:shadow-lg transition-all duration-200 cursor-pointer"
            >
              <div className="flex flex-col items-start">
                <div className="w-16 h-16 mb-4 flex items-center justify-center bg-[#468AFC]/10 rounded-lg group-hover:bg-[#3C39EE]/10">
                  <svg
                    className="w-8 h-8 text-[#468AFC] group-hover:text-[#3C39EE]"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"
                    />
                  </svg>
                </div>
                <div className="flex items-center mb-2">
                  <h3 className="text-xl font-semibold text-gray-950 mr-2">Your own data</h3>
                  <span className="px-2 py-1 text-xs font-medium text-gray-500 bg-gray-100 rounded">
                    Advanced
                  </span>
                </div>
                <p className="text-gray-600">
                  Connect to your data warehouse to get started with Compass.{' '}
                  <a
                    href="https://docs.compass.dagster.io/admins/adding-data"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[#3C39EE] hover:underline"
                    onClick={(e) => e.stopPropagation()}
                  >
                    Learn more ↗
                  </a>
                </p>
              </div>
            </div>
          </div>

          {/* Demo request text */}
          <div className="flex items-center justify-center mt-6">
            <p className="text-sm text-gray-600 text-center">
              Not sure which option is right for you?{' '}
              <a
                href="https://compass.dagster.io/request-a-demo?utm_source=app&utm_medium=in-app-link&utm_campaign=compass-demo-request&utm_content=signup_modal"
                className="text-[#3C39EE] hover:underline font-medium"
                target="_blank"
                rel="noopener noreferrer"
              >
                Request a demo
              </a>
            </p>
          </div>
        </div>
        {/* End white card wrapper */}

        {/* Footer Help Text */}
        <HelpFooter />

        {/* Compass Logo Mark */}
        <div className="mt-8 flex justify-center">
          <img src="/static/compass-logo-mark.svg" alt="Compass" className="h-12" />
        </div>
      </div>
    </div>
  );
}
