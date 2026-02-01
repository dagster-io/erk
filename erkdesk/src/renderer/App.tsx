import React from "react";
import SplitPane from "./components/SplitPane";
import PlanList from "./components/PlanList";

const App: React.FC = () => {
  return <SplitPane leftPane={<PlanList />} />;
};

export default App;
