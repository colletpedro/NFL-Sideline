import { Link, useLocation } from "react-router-dom";

interface SportsHeaderProps {
  updatedLabel: string;
}

function SportsHeader({ updatedLabel }: SportsHeaderProps) {
  const { pathname } = useLocation();

  return (
    <header className="sports-header">
      <div className="sports-header-inner">
        <Link to="/" className="sports-wordmark" aria-label="NFL Sideline — home">
          <span className="mark" aria-hidden="true" />
          NFL Sideline
        </Link>

        <nav className="sports-nav" aria-label="Primary">
          <Link to="/" className={`sports-nav-item ${pathname === "/" ? "active" : ""}`}>
            Games
          </Link>
          <span className="sports-nav-item inert">Predictions</span>
          <span className="sports-nav-item inert">Markets</span>
          <span className="sports-nav-item inert">Week 01</span>
        </nav>

        <div className="sports-meta">
          <span className="season">2026</span>
          <span className="week">Week 01</span>
          <span className={`updated ${updatedLabel.startsWith("Updated —") ? "" : "online"}`}>
            {updatedLabel}
          </span>
        </div>
      </div>
    </header>
  );
}

export default SportsHeader;