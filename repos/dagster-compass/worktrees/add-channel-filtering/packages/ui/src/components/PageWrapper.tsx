import {ReactNode} from 'react';
import {cn} from './utils';

interface PageWrapperProps {
  children: ReactNode;
  variant?: 'default' | 'full-height';
  className?: string;
}

/**
 * Base page wrapper that provides consistent background and layout structure.
 * Matches the body wrapper from Jinja layout.html.
 */
export function PageWrapper({children, variant = 'default', className}: PageWrapperProps) {
  return (
    <div
      className={cn(
        'bg-gray-50',
        variant === 'default' &&
          'min-h-screen flex flex-col items-center py-8 px-4 sm:px-6 lg:px-8',
        variant === 'full-height' && 'h-screen flex',
        className,
      )}
    >
      {children}
    </div>
  );
}
