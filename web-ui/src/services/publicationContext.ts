import { createContext, useContext } from "react";
import type { Game } from "./types";
import type { PublicationContext } from "./dataClient";

export interface PublicationState {
  publication: PublicationContext | null;
  games: Game[];
  loading: boolean;
  error: string | null;
  retry: () => void;
  selectedWeek: number | null;
  selectWeek: (week: number) => void;
  setDetailGame: (game: Game | null) => void;
}

export const Publication = createContext<PublicationState | null>(null);

export function usePublication(): PublicationState {
  const state = useContext(Publication);
  if (!state) throw new Error("Publication context missing");
  return state;
}
