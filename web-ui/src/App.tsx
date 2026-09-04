import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import GamesList from "./pages/GamesList";
import MatchupDashboard from "./pages/MatchupDashboard";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<GamesList />} />
          <Route path="/game/:id" element={<MatchupDashboard />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
