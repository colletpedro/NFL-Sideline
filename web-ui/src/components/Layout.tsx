import { Link } from "react-router-dom";
import type { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
}

function Layout({ children }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="masthead">
        <div className="masthead-top">
          <Link to="/" className="masthead-wordmark">
            NFL Sideline
          </Link>
          <div className="masthead-meta">
            <div>Vol. 01</div>
            <div>NFL / 2026</div>
          </div>
        </div>
        <div className="masthead-rule" aria-hidden="true" />
      </header>
      <main className="app-main">{children}</main>
      <footer className="pub-footer">
        <span>NFL Sideline — Sports Intelligence</span>
        <span>Model Release 01</span>
      </footer>
    </div>
  );
}

export default Layout;