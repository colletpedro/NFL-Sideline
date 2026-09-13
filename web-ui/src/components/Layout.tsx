import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import SportsHeader from "./SportsHeader";
import { dataClient } from "#runtime-client";
import { formatUpdated } from "../services/model";
import type { Game } from "../services/types";
import type { PublicationContext } from "../services/dataClient";
import { Publication } from "../services/publicationContext";
import { initialWeek } from "../services/calendar";

interface LayoutProps {
  children: ReactNode;
}

function Layout({ children }: LayoutProps) {
  const [publication, setPublication] = useState<PublicationContext | null>(null);
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [selectedWeek, selectWeek] = useState<number | null>(null);
  const [detailGame, setDetailGame] = useState<Game | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    dataClient
      .getPublicationContext()
      .then(async (context) => {
        const loadedGames = await dataClient.listGames(context.defaultSeason);
        if (!cancelled) {
          setPublication(context);
          setGames(loadedGames);
          selectWeek((previous) => previous !== null && loadedGames.some((g) => g.week === previous)
            ? previous : initialWeek(loadedGames, new Date()));
        }
      })
      .catch(() => {
        if (!cancelled) setError("The sideline is temporarily unavailable. Please try again.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [attempt]);

  const retry = () => {
    dataClient.clearCache();
    setAttempt((value) => value + 1);
  };
  const season = detailGame?.season ?? publication?.defaultSeason ?? null;
  const week = detailGame?.week ?? selectedWeek;

  return (
    <Publication.Provider value={{ publication, games, loading, error, retry, selectedWeek, selectWeek, setDetailGame }}>
    <div className="app-shell">
      <SportsHeader updatedLabel={formatUpdated(publication?.generatedAt)} season={season} week={week} />
      <main className="app-main">{children}</main>
      <footer className="site-footer">
        <div className="site-footer-inner">
          <span>NFL Sideline — Game Intelligence</span>
          {season !== null && <span>Season {season}</span>}
        </div>
      </footer>
    </div>
    </Publication.Provider>
  );
}

export default Layout;
