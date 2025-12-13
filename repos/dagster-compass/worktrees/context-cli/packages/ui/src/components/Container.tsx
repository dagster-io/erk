import {ReactNode} from 'react';
import {cn, CONTAINER_SIZE_CLASSES} from './utils';

interface ContainerProps {
  children: ReactNode;
  size?: keyof typeof CONTAINER_SIZE_CLASSES;
  className?: string;
}

/**
 * Max-width centering container.
 * Used for constraining content width while maintaining responsive design.
 */
export function Container({children, size = 'large', className}: ContainerProps) {
  return (
    <div className={cn('w-full mx-auto', CONTAINER_SIZE_CLASSES[size], className)}>{children}</div>
  );
}
