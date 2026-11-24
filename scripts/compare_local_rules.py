#!/usr/bin/env python3
"""Run all six known regressions and explicit synthetic examples, without any model or database.
Compares against immutable 1.0.0 artifacts. These cases are NOT an independent evaluation.
"""
import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / "editorial/local-rules-runs"
MANIFEST = ROOT / "editorial/evaluations/2026-09-26/cases.json"
JAR = ROOT / "core-api/target/core-api-0.1.0.jar"


def read(path):
    return json.loads(path.read_text())


def write(path, data):
    with path.open("x") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(name, pairs):
    evidence = []
    for team, metric, attack, defense in pairs:
        other = "BBB" if team == "AAA" else "AAA"
        for t, m, values in [(team, "OFF_EPA_" + metric, attack), (other, "DEF_EPA_" + metric, defense)]:
            for week, value in enumerate(values, 1):
                key = f"2026:{week}:{t}"
                evidence.append({"id": f"tw:{key}:{m}", "team": t, "metric": m, "season": 2026,
                                 "week": week, "origin": "CURRENT_SEASON_PRIOR_WEEKS", "value": value,
                                 "unit": "EPA", "volume": None, "sourceTable": "team_week_metrics", "sourceKey": key})
    return {"contract_version": 3, "game": {"game_id": name, "season": 2026, "week": 4, "phase": "REG"},
            "home_team": "AAA", "away_team": "BBB", "evidence": evidence}


def public_number(value):
    rounded = Decimal(str(value)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if not rounded:
        return "0,000 EPA" if Decimal(str(value)) == 0 else ("0 < EPA < 0,0005" if Decimal(str(value)) > 0 else "-0,0005 < EPA < 0")
    return f"{rounded:+.3f}".replace(".", ",") + " EPA"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="New output directory with existing parent")
    args = parser.parse_args()
    output = args.output.resolve()
    if "public" in output.parts:
        parser.error("Public output forbidden")
    output.mkdir()  # Never overwrite prior comparisons, including failures.
    java = str(Path(os.environ["JAVA_HOME"]) / "bin/java") if "JAVA_HOME" in os.environ else "java"
    cases = read(MANIFEST)["cases"]
    write(output / "run.json", {"startedAt": datetime.now(timezone.utc).isoformat(), "mode": "KNOWN_REGRESSION",
          "independentEvaluation": False, "jarSha256": sha(JAR), "manifestSha256": sha(MANIFEST),
          "cases": [c["gameId"] for c in cases], "caseSelection": "All six existing cases, no outcome-based sampling"})
    results, comparison = [], []

    def generate(context, directory):
        code = subprocess.run([java, "-jar", str(JAR), "editorial-local", str(context), str(directory)], cwd=ROOT).returncode
        result = read(directory / "result.json")
        results.append({"id": directory.name, "status": result["status"], "exitCode": code})
        if code:
            write(output / "results.json", {"results": results, "independentEvaluation": False})
            raise SystemExit(code)

    for case in cases:
        old_dir = OLD / ("development-final" if case["split"] == "development" else "holdout-v1") / case["gameId"]
        dest = output / case["gameId"]
        generate(MANIFEST.parent / case["context"], dest)
        old_selection, new_selection = read(old_dir / "selection.json"), read(dest / "selection.json")
        old_text, new_text = read(old_dir / "rendered.json"), read(dest / "rendered.json")
        old_classes = {c["id"]: c["classification"] for c in old_selection["candidates"]}
        primary = set(new_selection["document"]["sections"]["fator_chave"])
        numbers = []
        for candidate in new_selection["candidates"]:
            if candidate["id"] in primary:
                for side in ["attack", "defense"]:
                    value = public_number(candidate[side]["value"])
                    numbers.append({"candidate": candidate["id"], "side": side, "value": value,
                                    "presentBeforeInAdvantage": value in old_text["vantagem_tatica"],
                                    "presentNowInAdvantage": value in new_text["vantagem_tatica"]})
        comparison.append({"gameId": case["gameId"], "knownRegression": True,
             "sourceV1RenderSha256": sha(old_dir / "rendered.json"),
             "classifications": [{"id": c["id"], "before": old_classes[c["id"]], "after": c["classification"],
                                  "signals": c["signals"], "limitations": c["limitations"]} for c in new_selection["candidates"]],
             "before": old_text, "after": new_text, "principalNumbers": numbers,
             "groupings": new_selection["document"].get("groupings", []),
             "preservedPublicClaims": new_selection["document"]["sections"]["veredito"],
             "relations": new_selection["document"]["links"]})
    synthetic = output / "synthetic"
    synthetic.mkdir()
    fixtures = synthetic / "fixtures"
    fixtures.mkdir()
    repeated = lambda value: [value] * 3
    definitions = {
        "opposing-signs": [("AAA", "PASS", repeated(".2"), repeated("-.15"))],
        "weekly-variation": [("AAA", "PASS", ["-.1", ".4", ".2"], [".1", ".2", ".3"])],
        "tied-opportunities": [("AAA", "PASS", repeated(".111"), repeated(".222")),
                               ("AAA", "RUSH", repeated(".333"), repeated(".444"))],
        "both-teams": [("AAA", "PASS", repeated(".111"), repeated(".222")),
                       ("BBB", "RUSH", repeated(".333"), repeated(".444"))],
    }
    for name, pairs in definitions.items():
        path = fixtures / (name + ".json")
        write(path, fixture(name, pairs))
        generate(path, synthetic / name)
    write(output / "comparison.json", {"beforeVersion": "1.0.0", "afterVersion": "2.0.0", "cases": comparison,
                                       "independentEvaluation": False, "qualityEditorialProven": False})
    write(output / "results.json", {"results": results, "independentEvaluation": False, "qualityEditorialProven": False})
    lines = ["# Comparação local 1.0.0 → 2.0.0", "", "Os seis jogos são regressões conhecidas. Não há nova avaliação independente.", ""]
    for case in comparison:
        lines += ["## " + case["gameId"], "", "| Encontro | Classe anterior | Dimensões atuais |", "|---|---|---|"]
        for c in case["classifications"]:
            s = c["signals"]
            lines += [f"| {c['id']} | {c['before']} | ataque {s['attack']['pattern']}; defesa {s['defense']['pattern']}; {s['relation']} |"]
        lines += ["", "### Quatro blocos antes e depois", ""]
        for field in case["before"]:
            lines += [f"**{field} — antes**", "", case["before"][field], "", f"**{field} — agora**", "", case["after"][field], ""]
        introduced = [n for n in case["principalNumbers"] if not n["presentBeforeInAdvantage"] and n["presentNowInAdvantage"]]
        lines += ["**Números principais antes ausentes no bloco vantagem:** " + ("; ".join(n["candidate"] + " " + n["side"] + " " + n["value"] for n in introduced) or "nenhum"), "",
                  "**Panoramas omitidos apenas por redundância editorial:** " + (", ".join(g["candidateId"] for g in case["groupings"]) or "nenhum"), "",
                  "Todas as seis candidaturas, limitações, evidências e relações permanecem em selection.json. O validador exige representação pública ou agrupamento comprovável para cada par disponível.", ""]
    with (output / "COMPARISON.md").open("x") as f:
        f.write("\n".join(lines))
    examples = ["# Exemplos completos — contrato v5", "", "AAA e BBB são equipes fictícias; os exemplos sintéticos foram definidos por condições de sinal, sem seleção por resultado.", ""]
    for title, path in [("Oposição ataque/defesa — sintético", synthetic / "opposing-signs"),
                        ("Variação semanal — sintético", synthetic / "weekly-variation"),
                        ("Alternativas empatadas BAL–DAL — real, contexto congelado conhecido", output / "2026_03_BAL_DAL"),
                        ("Oportunidades dos dois lados — sintético", synthetic / "both-teams")]:
        examples += ["## " + title, ""]
        for field, value in read(path / "rendered.json").items():
            examples += ["**" + field + "**", "", value, ""]
    with (output / "EXAMPLES.md").open("x") as f:
        f.write("\n".join(examples))


if __name__ == "__main__":
    main()
