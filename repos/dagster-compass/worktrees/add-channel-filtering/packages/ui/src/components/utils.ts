/**
 * Design constants matching Jinja template layout.html
 */

export const CONTAINER_SIZE_CLASSES = {
  small: 'max-w-md',
  medium: 'max-w-lg',
  large: 'max-w-4xl',
  xl: 'max-w-6xl',
  '2xl': 'max-w-screen-2xl',
} as const;

export const BRAND_COLORS = {
  primary: '#3C39EE',
  lightBlue: '#468AFC',
} as const;

export const HEADER_SIZE_CLASSES = {
  normal: 'text-3xl',
  large: 'text-4xl',
} as const;

/**
 * Utility function to merge Tailwind CSS classes safely.
 * Handles conditional classes and resolves conflicts.
 */
export function cn(...classes: (string | undefined | null | false)[]): string {
  return classes.filter(Boolean).join(' ');
}
