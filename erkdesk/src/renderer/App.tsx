import React from "react";
import SplitPane from "./components/SplitPane";

const PlaceholderContent: React.FC = () => (
  <div style={{ padding: "1rem" }}>
    <h2 style={{ margin: "0 0 0.5rem" }}>Plans</h2>
    <ul style={{ paddingLeft: "1.25rem", margin: 0 }}>
      <li>Plan list will appear here</li>
      <li>Select a plan to view in the right pane</li>
    </ul>
  </div>
);

const App: React.FC = () => {
  return <SplitPane leftPane={<PlaceholderContent />} />;
};

export default App;
