import {ReactNode} from 'react';
import {cn, HEADER_SIZE_CLASSES} from './utils';

interface PageHeaderProps {
  logo?: ReactNode;
  icon?: ReactNode;
  title?: string;
  subtitle?: string;
  subtitleInfo?: string;
  size?: keyof typeof HEADER_SIZE_CLASSES;
  className?: string;
}

/**
 * Page header component with optional logo, icon, title, and subtitle.
 * Matches the header block from Jinja layout.html.
 */
export function PageHeader({
  logo,
  icon,
  title,
  subtitle,
  subtitleInfo,
  size = 'normal',
  className,
}: PageHeaderProps) {
  if (!logo && !icon && !title && !subtitle && !subtitleInfo) {
    return null;
  }

  return (
    <div className={cn('text-center mb-8', className)}>
      {logo && (
        <div className="mb-6 flex justify-center">
          {typeof logo === 'string' ? <img src={logo} alt="Logo" className="h-32 w-auto" /> : logo}
        </div>
      )}

      {icon && <div className="mb-4">{icon}</div>}

      {title && (
        <h2 className={cn('header-text font-semibold text-gray-900', HEADER_SIZE_CLASSES[size])}>
          {title}
        </h2>
      )}

      {subtitle && <p className="mt-4 text-lg text-gray-600 subheader-text">{subtitle}</p>}

      {subtitleInfo && (
        <div className="text-sm text-gray-500 max-w-md mx-auto mt-2 flex items-center justify-center gap-1">
          <i className="ph-bold ph-info text-gray-500 text-sm"></i>
          <span>{subtitleInfo}</span>
        </div>
      )}
    </div>
  );
}
