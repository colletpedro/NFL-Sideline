"""Piloto walk-forward 2013-2017 dos hiperparâmetros do Elo e do ridge de `models/ratings.py` (H6).

Reproduz a escolha dos hiperparâmetros com a MESMA matemática de `model_code/ratings_pyfunc.py`, mas só com jogos de
2011..2017: o script descarta toda linha de 2018+ logo depois de carregar e ANTES de qualquer cálculo (`restrict`),
e `run_pilot` recusa qualquer quadro com temporada acima de `PILOT_LAST_SEASON`. Splits: um por SEMANA de cada
temporada 2013..2017, cada um treinado com todos os jogos anteriores a ela (jogos de 2011+). Métrica: RMSE pooled.

Grade do Elo: k {0,03; 0,05; 0,07; 0,1; 0,15} x hfa {1,5; 2; 2,5; 3} x teto {21; 28; 40} x reversão {0,2; 1/3; 0,5}.
Grade do ridge: lambda {1; 5; 10} x meia-vida {17; 34; 52} semanas. Saída: só métricas agregadas
(`ratings_pilot_results.json` e `.md`, nesta pasta).

Uso: `python pilots/ratings_pilot.py [--home DIR] [--build-id ID]`.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from models import ratings as R  # noqa: E402

pf = R.pf
PILOT_FIRST_TEST, PILOT_LAST_SEASON = 2013, 2017
ELO_GRID = {"k": [0.03, 0.05, 0.07, 0.1, 0.15], "hfa": [1.5, 2.0, 2.5, 3.0], "cap": [21.0, 28.0, 40.0],
            "reversion": [0.2, 1.0 / 3.0, 0.5]}
RIDGE_GRID = {"lam": [1.0, 5.0, 10.0], "halflife": [17.0, 34.0, 52.0]}
USED_ELO = dict(R.ELO)
USED_RIDGE = [{"lam": R.RIDGE_LAMBDA, "halflife": h} for h in R.RIDGE_HALFLIVES.values()]


def restrict(df: pd.DataFrame) -> pd.DataFrame:
    """Descarta toda linha de temporada > 2017. Deve ser a primeira coisa feita com os dados carregados."""
    out = df[df["season"] <= PILOT_LAST_SEASON].copy().reset_index(drop=True)
    if len(out) and int(out["season"].max()) > PILOT_LAST_SEASON:
        raise RuntimeError("piloto com temporada fora do período permitido")
    return out


def pilot_splits(df: pd.DataFrame) -> list:
    """[(season, week, índices de treino, índices de teste)] por semana de 2013..2017; treino = tudo antes da semana."""
    if int(df["season"].max()) > PILOT_LAST_SEASON:
        raise RuntimeError(f"o piloto só pode ver temporadas <= {PILOT_LAST_SEASON}")
    key = df["season"].to_numpy() * 100 + df["week"].to_numpy()
    out = []
    for s in range(PILOT_FIRST_TEST, PILOT_LAST_SEASON + 1):
        for w in sorted(int(x) for x in df.loc[df["season"] == s, "week"].unique()):
            k = s * 100 + w
            out.append((s, w, np.flatnonzero(key < k), np.flatnonzero(key == k)))
    return out


def _squared_errors(df, splits, fit):
    sq = []
    for _s, _w, tr, te in splits:
        params = fit(df.iloc[tr])
        t = df.iloc[te]
        p = pf.predict_margin(params, t["home_team"], t["away_team"], t["neutral"].to_numpy(dtype=bool),
                              t["season"].to_numpy())
        sq.append((t["result"].to_numpy(dtype="float64") - p) ** 2)
    return np.concatenate(sq)


def run_pilot(df: pd.DataFrame) -> dict:
    """Roda as duas grades sobre `df` (já restrito a <= 2017) e devolve as métricas agregadas."""
    splits = pilot_splits(df)
    n = int(sum(len(te) for *_x, te in splits))
    elo = []
    for k, hfa, cap, rev in itertools.product(*ELO_GRID.values()):
        sq = _squared_errors(df, splits, lambda h: pf.elo_fit(h, k, hfa, cap, rev))
        elo.append({"k": k, "hfa": hfa, "cap": cap, "reversion": rev, "rmse": float(np.sqrt(sq.mean()))})
    ridge = []
    for lam, hl in itertools.product(*RIDGE_GRID.values()):
        sq = _squared_errors(df, splits, lambda h: pf.ridge_fit(h, hl, lam))
        ridge.append({"lam": lam, "halflife_weeks": hl, "rmse": float(np.sqrt(sq.mean()))})
    elo.sort(key=lambda r: r["rmse"])
    ridge.sort(key=lambda r: r["rmse"])

    def near(r):
        return all(abs(r[a] - USED_ELO[a]) < 1e-9 for a in ("k", "hfa", "cap", "reversion"))
    used_elo = next(r for r in elo if near(r))
    used_ridge = [next(r for r in ridge if r["lam"] == u["lam"] and r["halflife_weeks"] == u["halflife"])
                  for u in USED_RIDGE]
    return {"period": {"test_seasons": [PILOT_FIRST_TEST, PILOT_LAST_SEASON], "train_from_season": R.FIRST_TRAIN_SEASON,
                       "max_season_read": int(df["season"].max()), "n_test_games": n, "n_splits": len(splits),
                       "metric": "rmse pooled, walk-forward semanal"},
            "elo": {"grid": {a: list(v) for a, v in ELO_GRID.items()}, "n_configs": len(elo), "best": elo[0],
                    "best_rank": 1, "used": {**used_elo, "rank": elo.index(used_elo) + 1},
                    "rmse_gap_used_vs_best": used_elo["rmse"] - elo[0]["rmse"], "top10": elo[:10]},
            "ridge": {"grid": {a: list(v) for a, v in RIDGE_GRID.items()}, "n_configs": len(ridge), "best": ridge[0],
                      "used": [{**u, "rank": ridge.index(u) + 1} for u in used_ridge],
                      "all": ridge}}


def to_markdown(res: dict) -> str:
    p, e, g = res["period"], res["elo"], res["ridge"]
    L = ["# Piloto walk-forward 2013-2017 dos ratings (H6)", "",
         f"Só jogos de 2011..{p['max_season_read']}; {p['n_splits']} splits semanais, {p['n_test_games']} jogos testados "
         f"({p['test_seasons'][0]}-{p['test_seasons'][1]}). Métrica: RMSE pooled. Nenhuma linha de 2018+ foi lida.", "",
         "## Elo", "", f"{e['n_configs']} configurações. Usado no hub: k={e['used']['k']}, hfa={e['used']['hfa']}, "
         f"teto={e['used']['cap']}, reversão={e['used']['reversion']:.4f} (RMSE {e['used']['rmse']:.5f}, posição "
         f"{e['used']['rank']} de {e['n_configs']}). Ótimo do piloto: k={e['best']['k']}, hfa={e['best']['hfa']}, "
         f"teto={e['best']['cap']}, reversão={e['best']['reversion']:.4f} (RMSE {e['best']['rmse']:.5f}). Diferença "
         f"usado - ótimo: {e['rmse_gap_used_vs_best']:.5f}.", "",
         "| # | k | hfa | teto | reversão | RMSE |", "|---|---|---|---|---|---|"]
    L += [f"| {i} | {r['k']} | {r['hfa']} | {r['cap']} | {r['reversion']:.4f} | {r['rmse']:.5f} |"
          for i, r in enumerate(e["top10"], 1)]
    L += ["", "## Ridge com decaimento", "", f"Ótimo do piloto: λ={g['best']['lam']}, meia-vida={g['best']['halflife_weeks']} "
          f"(RMSE {g['best']['rmse']:.5f}). Valores usados no hub: " +
          "; ".join(f"λ={u['lam']}, meia-vida={u['halflife_weeks']} (RMSE {u['rmse']:.5f}, posição {u['rank']} de "
                    f"{g['n_configs']})" for u in g["used"]) + ".", "",
          "| # | λ | meia-vida | RMSE |", "|---|---|---|---|"]
    L += [f"| {i} | {r['lam']} | {r['halflife_weeks']} | {r['rmse']:.5f} |" for i, r in enumerate(g["all"], 1)]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--home", default=None)
    ap.add_argument("--build-id", default=None)
    ap.add_argument("--out-dir", default=str(HERE))
    a = ap.parse_args(argv)
    df, _info, _asof = R.load_data(a.build_id, a.home)
    df = restrict(df)  # antes de qualquer cálculo
    res = run_pilot(df)
    out = Path(a.out_dir)
    (out / "ratings_pilot_results.json").write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n")
    (out / "ratings_pilot_results.md").write_text(to_markdown(res))
    print(to_markdown(res))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
