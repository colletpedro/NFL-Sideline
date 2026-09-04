import { BrowserRouter, Routes, Route } from "react-router-dom";
import GamesList from "./pages/GamesList";
import MatchupDashboard from "./pages/MatchupDashboard";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<GamesList />} />
        <Route path="/game/:id" element={<MatchupDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
