import {ReactNode} from 'react';
import {cn, CONTAINER_SIZE_CLASSES} from './utils';

interface CardProps {
  children: ReactNode;
  size?: keyof typeof CONTAINER_SIZE_CLASSES;
  className?: string;
  withHover?: boolean;
}

/**
 * White card component with rounded corners, border, and shadow.
 * Matches the content_wrapper block from Jinja layout.html.
 */
export function Card({children, size = 'medium', className, withHover = true}: CardProps) {
  return (
    <div
      className={cn(
        'w-full mx-auto bg-white rounded-2xl border border-gray-200 shadow-xl p-8 sm:p-6',
        withHover && 'transition-all duration-300 hover:shadow-2xl',
        CONTAINER_SIZE_CLASSES[size],
        className,
      )}
    >
      {children}
    </div>
  );
}
