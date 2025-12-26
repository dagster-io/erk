import {ReactNode} from 'react';
import {Link, useLocation} from 'react-router-dom';
import {useUserProfile} from '../contexts/UserProfileContext';
import {cn} from './utils';

export interface NavItem {
  path: string;
  label: string;
  icon: ReactNode;
  badge?: number | null;
}

interface SidebarProps {
  children: ReactNode;
  className?: string;
}

/**
 * Main sidebar container component.
 * Provides fixed-width sidebar with flexbox layout for logo, nav, and user profile.
 */
export function Sidebar({children, className}: SidebarProps) {
  return (
    <div className={cn('w-56 bg-white border-r border-slate-200 flex flex-col h-full', className)}>
      {children}
    </div>
  );
}

interface SidebarLogoProps {
  src: string;
  alt?: string;
  width?: string;
  className?: string;
}

/**
 * Sidebar logo component.
 */
export function SidebarLogo({src, alt = 'Logo', width = '140px', className}: SidebarLogoProps) {
  return (
    <div className={cn('px-6 py-8 border-b border-slate-200', className)}>
      <img src={src} alt={alt} style={{width}} />
    </div>
  );
}

interface SidebarNavProps {
  items: NavItem[];
  className?: string;
}

/**
 * Sidebar navigation component with active state highlighting.
 */
export function SidebarNav({items, className}: SidebarNavProps) {
  const location = useLocation();

  return (
    <nav className={cn('flex-1 overflow-auto px-4 py-3', className)}>
      <div className="space-y-0.5">
        {items.map((item) => {
          const isActive =
            location.pathname === item.path || location.pathname.startsWith(item.path + '/');
          return (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors text-sm',
                isActive
                  ? 'bg-[#468AFC]/10 text-blue-700 font-semibold'
                  : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium',
              )}
            >
              <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
                {item.icon}
              </div>
              <span>{item.label}</span>
              {item.badge !== undefined && item.badge !== null && item.badge > 0 && (
                <span className="ml-auto inline-flex items-center justify-center min-w-[20px] h-5 px-1.5 text-xs font-medium text-white bg-[#3C39EE] rounded-full">
                  {item.badge}
                </span>
              )}
            </Link>
          );
        })}
      </div>
    </nav>
  );
}

interface SidebarFooterLinksProps {
  className?: string;
}

/**
 * Sidebar footer links for docs and support.
 */
export function SidebarFooterLinks({className}: SidebarFooterLinksProps) {
  return (
    <div className={cn('px-4 py-4 border-t border-slate-200', className)}>
      <div className="space-y-1">
        <a
          href="https://docs.compass.dagster.io/"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium"
        >
          <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
            <i className="ph-bold ph-notebook text-xl" />
          </div>
          <span>Docs</span>
        </a>
        <a
          href="mailto:compass-support@dagsterlabs.com"
          className="flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors text-sm text-slate-600 hover:bg-slate-50 hover:text-slate-900 font-medium"
        >
          <div className="w-5 h-5 flex items-center justify-center flex-shrink-0">
            <i className="ph-bold ph-question text-xl" />
          </div>
          <span>Email Support</span>
        </a>
      </div>
    </div>
  );
}

interface SidebarUserProfileProps {
  className?: string;
}

/**
 * Sidebar user profile component showing avatar and name.
 */
export function SidebarUserProfile({className}: SidebarUserProfileProps) {
  const {profile, loading} = useUserProfile();

  return (
    <div className={cn('px-4 py-5 border-t border-slate-200', className)}>
      {loading ? (
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="w-9 h-9 bg-slate-200 rounded-full animate-pulse" />
          <div className="flex-1">
            <div className="h-3.5 bg-slate-200 rounded animate-pulse mb-2 w-24" />
            <div className="h-3 bg-slate-100 rounded animate-pulse w-16" />
          </div>
        </div>
      ) : profile ? (
        <div className="flex items-center gap-3 px-2 py-1">
          {profile.avatar_url ? (
            <img
              src={profile.avatar_url}
              alt={profile.display_name}
              className="w-9 h-9 rounded-full"
            />
          ) : (
            <div className="w-9 h-9 bg-slate-300 rounded-full flex items-center justify-center text-slate-700 text-sm font-medium">
              {profile.display_name.charAt(0).toUpperCase()}
            </div>
          )}
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-slate-900 truncate">
              {profile.display_name}
            </div>
            {profile.real_name && profile.real_name !== profile.display_name && (
              <div className="text-xs text-slate-500 truncate">{profile.real_name}</div>
            )}
          </div>
        </div>
      ) : null}
    </div>
  );
}
