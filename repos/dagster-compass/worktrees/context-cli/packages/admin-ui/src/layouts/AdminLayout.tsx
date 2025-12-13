import { Outlet, NavLink } from 'react-router-dom'

export function AdminLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <nav className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-8">
              <h1 className="text-xl font-bold text-gray-900">Compass Admin Panel</h1>
              <div className="flex space-x-4">
                <NavLink
                  to="/organizations"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Organizations
                </NavLink>
                <NavLink
                  to="/tokens"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Invite Tokens
                </NavLink>
                <NavLink
                  to="/onboarding"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Onboarding
                </NavLink>
                <NavLink
                  to="/analytics"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Analytics
                </NavLink>
                <NavLink
                  to="/threads"
                  className={({ isActive }) => (isActive ? 'nav-link active' : 'nav-link')}
                >
                  Threads
                </NavLink>
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  )
}
