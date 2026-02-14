import './ModeToggle.css';

export type AppMode = 'dashboard' | 'review';

interface ModeToggleProps {
  mode: AppMode;
  onModeChange: (mode: AppMode) => void;
}

export function ModeToggle({mode, onModeChange}: ModeToggleProps) {
  return (
    <div className="mode-toggle">
      <span className="mode-toggle-logo">erk</span>
      <button
        className={`mode-toggle-btn ${mode === 'dashboard' ? 'active' : ''}`}
        onClick={() => onModeChange('dashboard')}
      >
        Dashboard
      </button>
      <button
        className={`mode-toggle-btn ${mode === 'review' ? 'active' : ''}`}
        onClick={() => onModeChange('review')}
      >
        Review plans
      </button>
    </div>
  );
}
