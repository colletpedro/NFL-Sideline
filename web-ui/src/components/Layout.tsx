import { Trophy } from "lucide-react";
import { Link } from "react-router-dom";
import type { ReactNode } from "react";

interface LayoutProps {
  children: ReactNode;
}

function Layout({ children }: LayoutProps) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <Link to="/" className="app-brand">
          <Trophy size={22} aria-hidden="true" />
          <span>NFL Sideline</span>
        </Link>
      </header>
      <main className="app-main">{children}</main>
    </div>
  );
}

export default Layout;
