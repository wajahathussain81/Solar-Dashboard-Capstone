import React from "react";
import {
  BrowserRouter as Router,
  Route,
  Routes,
  useLocation,
} from "react-router-dom";
import { motion, AnimatePresence } from "framer-motion";
import DailyProductionPage from "./components/DailyProductionPage";
import SiteAlertsPage from "./components/SiteAlertsPage";
import MetricsPage from "./components/MetricsPage";
import FifteenMinPage from "./components/FifteenMinPage";

//Added transitions to navigation of the sites betwenn sites
const RouteContainer = ({ children }) => {
  const location = useLocation();

  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        style={{ position: "absolute", width: "100%" }}
      >
        {children}
      </motion.div>
    </AnimatePresence>
  );
};

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route
            path="/"
            element={
              <RouteContainer>
                <FifteenMinPage />
              </RouteContainer>
            }
          />
          <Route
            path="/ProductionData_fifteen"
            element={
              <RouteContainer>
                <FifteenMinPage />
              </RouteContainer>
            }
          />
          <Route
            path="/ProductionData_daily"
            element={
              <RouteContainer>
                <DailyProductionPage />
              </RouteContainer>
            }
          />
          <Route
            path="/Alerts"
            element={
              <RouteContainer>
                <SiteAlertsPage />
              </RouteContainer>
            }
          />
          <Route
            path="/Metrics"
            element={
              <RouteContainer>
                <MetricsPage />
              </RouteContainer>
            }
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
