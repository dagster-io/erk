import {ReactNode, useMemo} from 'react';
import {PageWrapper} from '../components/PageWrapper';
import {
  Sidebar,
  SidebarLogo,
  SidebarNav,
  SidebarFooterLinks,
  SidebarUserProfile,
  NavItem,
} from '../components/Sidebar';
import {useGovernanceCount} from '../contexts/GovernanceCountContext';
import {GovernanceCountProvider} from '../contexts/GovernanceCountProvider';

interface SidebarLayoutProps {
  children: ReactNode;
  navItems?: NavItem[];
}

const DEFAULT_NAV_ITEMS: NavItem[] = [
  {
    path: '/connections',
    label: 'Connections',
    icon: <i className="ph-bold ph-database text-xl" />,
  },
  {
    path: '/channels',
    label: 'Channels',
    icon: <i className="ph-bold ph-hash text-xl" />,
  },
  {
    path: '/context-governance',
    label: 'Governance',
    icon: <i className="ph-bold ph-shield-check text-xl" />,
  },
  {
    path: '/billing',
    label: 'Billing & Usage',
    icon: <i className="ph-bold ph-gauge text-xl" />,
  },
  {
    path: '/referral',
    label: 'Refer a friend',
    icon: <i className="ph-bold ph-hand text-xl" />,
  },
];

/**
 * Layout with fixed sidebar navigation and main content area.
 * Replaces LoggedInLayout with a compositional approach.
 * Used for dashboard pages.
 */
export function SidebarLayoutContents({navItems}: {navItems: NavItem[]}) {
  const {count: governanceCount} = useGovernanceCount();

  // Enhance nav items with governance count badge
  const enhancedNavItems = useMemo(() => {
    return navItems.map((item) => {
      if (item.path === '/context-governance') {
        return {...item, badge: governanceCount};
      }
      return item;
    });
  }, [navItems, governanceCount]);

  return (
    <Sidebar>
      <SidebarLogo src="/static/compass-logo.svg" alt="Compass Logo" />
      <SidebarNav items={enhancedNavItems} />
      <SidebarFooterLinks />
      <SidebarUserProfile />
    </Sidebar>
  );
}

/**
 * Layout with fixed sidebar navigation and main content area.
 * Replaces LoggedInLayout with a compositional approach.
 * Used for dashboard pages.
 */
export function SidebarLayout({children, navItems = DEFAULT_NAV_ITEMS}: SidebarLayoutProps) {
  return (
    <PageWrapper variant="full-height">
      <GovernanceCountProvider>
        <SidebarLayoutContents navItems={navItems} />
        <div className="flex-1 overflow-auto h-full bg-gray-50">{children}</div>
      </GovernanceCountProvider>
    </PageWrapper>
  );
}
