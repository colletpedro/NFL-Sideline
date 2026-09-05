import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import SportsHeader from "./SportsHeader";
import { api } from "../services/api";
import { formatUpdated } from "../services/model";
import type { Game } from "../services/types";

const SEASON = 2026;

function latestUpdated(games: Game[]): string | null {
  let latest: string | null = null;
  for (const g of games) {
    if (g.updatedAt && (!latest || g.updatedAt > latest)) latest = g.updatedAt;
  }
  return latest;
}

interface LayoutProps {
  children: ReactNode;
}

function Layout({ children }: LayoutProps) {
  const [updatedLabel, setUpdatedLabel] = useState("Updated —");

  useEffect(() => {
    let cancelled = false;
    api
      .get<Game[]>("/games", { params: { season: SEASON } })
      .then((r) => {
        const ts = latestUpdated(r.data);
        if (!cancelled && ts) setUpdatedLabel(formatUpdated(ts));
      })
      .catch(() => {
        /* header meta is optional */
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="app-shell">
      <SportsHeader updatedLabel={updatedLabel} />
      <main className="app-main">{children}</main>
      <footer className="site-footer">
        <div className="site-footer-inner">
          <span>NFL Sideline — Game Intelligence</span>
          <span>Model Release 01 · Season 2026</span>
        </div>
      </footer>
    </div>
  );
}

export default Layout;