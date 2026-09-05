import { BrowserRouter, Routes, Route } from "react-router-dom";
import Layout from "./components/Layout";
import Home from "./pages/Home";
import MatchupDashboard from "./pages/MatchupDashboard";

function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/game/:id" element={<MatchupDashboard />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;