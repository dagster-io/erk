import {ReactNode} from 'react';

interface MarketingLayoutProps {
  children: ReactNode;
}

/**
 * Two-column marketing layout matching Jinja's use_marketing_layout=true.
 * Left column contains content, right column shows branding with dark blue gradient.
 */
export function MarketingLayout({children}: MarketingLayoutProps) {
  return (
    <div className="min-h-screen flex">
      {/* Left Column: Content */}
      <div className="w-full lg:w-1/2 bg-gray-50 flex flex-col items-center overflow-y-auto">
        <div className="mt-24 w-full max-w-md flex flex-col items-center">{children}</div>
      </div>

      {/* Right Column: Dark Blue Background with Subtle Gradient */}
      <div className="hidden lg:block lg:w-1/2 bg-dark-blue-gradient relative">
        {/* Compass Feature Content */}
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <img
            src="/static/compass-feature.png"
            alt="Compass Feature"
            className="w-1/5 lg:w-3/5 object-contain"
          />
          <h1 className="text-white/90 lg:text-4xl xl:text-5xl mt-12 text-center max-w-lg leading-tight font-serif">
            Finally, data in everyone's hands.
          </h1>
          <img src="/static/compass-logo-white.svg" alt="Compass Logo" className="mt-8 h-9" />
        </div>
      </div>
    </div>
  );
}
