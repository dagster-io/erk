import '@blueprintjs/core/lib/css/blueprint.css';
import {StrictMode, useEffect} from 'react';
import {createRoot} from 'react-dom/client';

import {App} from './App.js';

function Root() {
  useEffect(() => {
    document.body.classList.add('bp5-dark');
  }, []);

  return <App />;
}

const rootEl = document.getElementById('root');
if (!rootEl) {
  throw new Error('Root element not found');
}
createRoot(rootEl).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
