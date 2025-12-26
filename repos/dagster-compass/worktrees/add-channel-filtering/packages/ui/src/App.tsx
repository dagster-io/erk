import {BrowserRouter as Router, Routes, Route, Outlet} from 'react-router-dom';
import {useEffect} from 'react';
import {UserProfileProvider} from './contexts/UserProfileProvider';
import {SidebarLayout} from './layouts/SidebarLayout';
import {MarketingLayout} from './layouts/MarketingLayout';
import Billing from './Billing';
import Onboarding from './Onboarding';
import Connections from './Connections';
import ConnectionsPage from './ConnectionsPage';
import ChannelsPage from './ChannelsPage';
import ContextGovernancePage from './ContextGovernancePage';
import Signup from './Signup';
import Thread from './Thread';
import DatasetSyncProgress from './DatasetSyncProgress';
import Referral from './Referral';
import OrgUsersPage from './OrgUsersPage';

function RedirectToCompass() {
  useEffect(() => {
    window.location.href = 'https://compass.dagster.io/';
  }, []);
  return null;
}

function App() {
  return (
    <Router>
      <UserProfileProvider>
        <Routes>
          <Route path="/" element={<RedirectToCompass />} />

          {/* Dashboard routes with sidebar */}
          <Route
            element={
              <SidebarLayout>
                <Outlet />
              </SidebarLayout>
            }
          >
            <Route path="/billing" element={<Billing />} />
            <Route path="/connections" element={<ConnectionsPage />} />
            <Route path="/connections/add-connection" element={<Connections />} />
            <Route path="/channels" element={<ChannelsPage />} />
            <Route path="/context-governance" element={<ContextGovernancePage />} />
            <Route path="/dataset-sync" element={<DatasetSyncProgress />} />
            <Route path="/users" element={<OrgUsersPage />} />
            <Route path="/referral" element={<Referral />} />
          </Route>

          {/* Marketing layout routes (signup/onboarding) */}
          <Route
            element={
              <MarketingLayout>
                <Outlet />
              </MarketingLayout>
            }
          >
            <Route path="/onboarding" element={<Onboarding />} />
          </Route>

          {/* Pages with custom layouts */}
          <Route path="/signup" element={<Signup />} />
          <Route path="/onboarding/connections" element={<Connections />} />
          <Route path="/thread/:team_id/:channel_id/:thread_ts" element={<Thread />} />
        </Routes>
      </UserProfileProvider>
    </Router>
  );
}

export default App;
