import Stepper from './Stepper';

interface WizardLayoutProps {
  currentStep: number; // 1-4
  children: React.ReactNode;
}

export default function WizardLayout({currentStep, children}: WizardLayoutProps) {
  return (
    <div className="min-h-screen bg-gray-50 px-4 sm:px-6 lg:px-8 py-8 pb-12 md:pb-16 lg:pb-24">
      <div className="max-w-screen-2xl mx-auto mt-4 sm:mt-6 md:mt-8 lg:mt-12">
        <div className="grid grid-cols-1 md:grid-cols-[260px_1fr] gap-y-8 md:gap-y-10 lg:gap-y-12 gap-x-10 xl:gap-x-12 2xl:gap-x-16">
          {/* Stepper Column */}
          <div>
            <Stepper currentStep={currentStep} />
          </div>

          {/* Form Column */}
          <div className="w-full">
            <div className="max-w-[768px] bg-white rounded-2xl border border-slate-200 shadow-sm p-4 sm:p-5 md:p-6 lg:p-7">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
