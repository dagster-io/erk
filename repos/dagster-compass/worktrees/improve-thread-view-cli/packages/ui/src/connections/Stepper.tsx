interface StepperProps {
  currentStep: number; // 1-4
}

const steps = [
  {num: 1, title: 'Connection Setup', subtitle: 'Configure warehouse credentials'},
  {num: 2, title: 'Select Schemas', subtitle: 'Choose database schemas to include'},
  {num: 3, title: 'Select Tables & Verify', subtitle: 'Pick tables and verify permissions'},
  {num: 4, title: 'Connect to Channels', subtitle: 'Connect channels and finish setup'},
];

export default function Stepper({currentStep}: StepperProps) {
  return (
    <div className="md:sticky md:top-8 md:self-start">
      {/* Compass Logo for mobile */}
      <div className="md:hidden flex justify-center mb-4">
        <img src="/static/compass-logo.svg" alt="Compass" className="h-7" />
      </div>

      {/* Horizontal stepper for mobile */}
      <div className="md:hidden flex items-center justify-center py-4 px-2">
        <div className="flex items-center space-x-2">
          {steps.map((step, index) => (
            <div key={step.num} className="flex items-center">
              <div
                className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 ${
                  step.num < currentStep
                    ? 'bg-[#3C39EE]'
                    : step.num === currentStep
                      ? 'bg-[#3C39EE] ring-2 ring-[#3C39EE]/20'
                      : 'bg-gray-200'
                }`}
              >
                <span
                  className={`text-xs font-medium ${
                    step.num < currentStep
                      ? 'text-white'
                      : step.num === currentStep
                        ? 'text-white'
                        : 'text-gray-500'
                  }`}
                >
                  {step.num < currentStep ? '✓' : step.num}
                </span>
              </div>
              {index < steps.length - 1 && (
                <div
                  className={`w-6 h-0.5 mx-1 ${step.num < currentStep ? 'bg-[#3C39EE]' : 'bg-gray-200'}`}
                />
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Vertical stepper for desktop */}
      <div className="hidden md:block pt-6 md:pt-8 lg:pt-10 text-sm leading-tight relative">
        {steps.map((step, index) => (
          <div key={step.num} className="flex items-start space-x-3">
            <div className="flex flex-col items-center">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  step.num < currentStep
                    ? 'bg-[#3C39EE]'
                    : step.num === currentStep
                      ? 'bg-[#3C39EE] ring-4 ring-[#3C39EE]/20'
                      : 'bg-gray-200'
                }`}
              >
                <span
                  className={`text-sm font-medium ${
                    step.num < currentStep
                      ? 'text-white'
                      : step.num === currentStep
                        ? 'text-white'
                        : 'text-gray-500'
                  }`}
                >
                  {step.num < currentStep ? '✓' : step.num}
                </span>
              </div>
              {index < steps.length - 1 && <div className="w-0.5 h-4 bg-gray-200 mt-2" />}
            </div>
            <div className={`pt-1 ${index < steps.length - 1 ? 'pb-6' : ''}`}>
              <div
                className={`text-sm font-medium ${step.num === currentStep ? 'text-[#3C39EE]' : 'text-slate-500'}`}
              >
                {step.title}
              </div>
              <div className="text-xs text-slate-500">{step.subtitle}</div>
            </div>
          </div>
        ))}

        {/* Compass Logo at bottom of stepper */}
        <div className="hidden md:flex mt-8">
          <img src="/static/compass-logo.svg" alt="Compass" className="h-7" />
        </div>
      </div>
    </div>
  );
}
