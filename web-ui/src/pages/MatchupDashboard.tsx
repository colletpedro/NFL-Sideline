import { useParams } from "react-router-dom";

function MatchupDashboard() {
  const { id } = useParams<{ id: string }>();

  return <h1>Matchup Analysis: {id}</h1>;
}

export default MatchupDashboard;
