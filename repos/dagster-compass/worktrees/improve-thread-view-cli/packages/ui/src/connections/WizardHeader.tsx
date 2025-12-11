interface WizardHeaderProps {
  onBack: () => void;
  backText: string;
  icon?: string; // Optional warehouse icon path
  title: string;
  subtitle?: string;
}

export default function WizardHeader({onBack, backText, icon, title, subtitle}: WizardHeaderProps) {
  return (
    <div className="mb-8">
      {/* Back Button */}
      <button
        onClick={onBack}
        className="inline-flex items-center text-sm text-slate-500 hover:text-slate-700 mb-4"
      >
        <svg className="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 19l-7-7 7-7" />
        </svg>
        {backText}
      </button>

      {/* Title with Optional Icon */}
      <div className="flex items-center gap-1 mb-2">
        {icon && (
          <div className="w-9 h-9 flex-shrink-0 flex items-center justify-center">
            <img src={icon} alt="" className="h-9 w-9" />
          </div>
        )}
        <h1 className="text-xl font-semibold text-slate-900">{title}</h1>
      </div>

      {/* Subtitle */}
      {subtitle && <p className="text-sm text-slate-600">{subtitle}</p>}
    </div>
  );
}
