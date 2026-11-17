"""Métricas de jogo (por partida e por time) a partir dos eventos StatsBomb."""
from __future__ import annotations

from collections import Counter

import pandas as pd

from src.data import TEAM, events, matches, three_sixty

DEF_ACTIONS = {"Interception", "Foul Committed", "Dribbled Past"}  # + desarmes (Duel/Tackle), tratados abaixo


def _is_def_action(e) -> bool:
    t = e["type"]["name"]
    return t in DEF_ACTIONS or (t == "Duel" and e["duel"]["type"]["name"] == "Tackle")


def match_summary(match_id: int) -> dict:
    """Resumo de um jogo: posse, passes, finalizações, xG, PPDA, field tilt, formação e cobertura 360."""
    ev = [e for e in events(match_id) if e["period"] <= 4]
    ff = three_sixty(match_id)
    teams = {e["team"]["name"] for e in ev}
    opp = (teams - {TEAM}).pop()
    out = {"match_id": match_id}

    # posse por tempo (soma da duração dos eventos de cada posse)
    dur = Counter()
    for e in ev:
        dur[e["possession_team"]["name"]] += e.get("duration") or 0
    out["posse"] = dur[TEAM] / (dur[TEAM] + dur[opp])

    for side, name in (("", TEAM), ("opp_", opp)):
        te = [e for e in ev if e["team"]["name"] == name]
        passes = [e for e in te if e["type"]["name"] == "Pass"]
        ok = [p for p in passes if "outcome" not in p["pass"]]
        shots = [e for e in te if e["type"]["name"] == "Shot"]
        np_shots = [s for s in shots if s["shot"]["type"]["name"] != "Penalty"]
        out[f"{side}passes"] = len(passes)
        out[f"{side}pass_pct"] = len(ok) / len(passes)
        out[f"{side}shots"] = len(shots)
        out[f"{side}np_xg"] = sum(s["shot"]["statsbomb_xg"] for s in np_shots)
        out[f"{side}xg"] = sum(s["shot"]["statsbomb_xg"] for s in shots)
        out[f"{side}final_third_passes"] = sum(1 for p in ok if p["pass"]["end_location"][0] >= 80)
        out[f"{side}pressures"] = sum(e["type"]["name"] == "Pressure" for e in te)
        xi = next(e for e in te if e["type"]["name"] == "Starting XI")
        out[f"{side}formation"] = str(xi["tactics"]["formation"])

    # PPDA: passes do adversário no próprio campo de defesa (60%) / ações defensivas nossas nessa zona
    def ppda(defender, attacker):
        att_passes = sum(1 for e in ev if e["team"]["name"] == attacker and e["type"]["name"] == "Pass"
                         and e["location"][0] <= 72)
        def_acts = sum(1 for e in ev if e["team"]["name"] == defender and _is_def_action(e)
                       and e["location"][0] >= 48)
        return att_passes / max(def_acts, 1)
    out["ppda"] = ppda(TEAM, opp)
    out["opp_ppda"] = ppda(opp, TEAM)

    # field tilt: % dos passes certos no terço final que são nossos
    out["field_tilt"] = out["final_third_passes"] / (out["final_third_passes"] + out["opp_final_third_passes"])

    # cobertura 360
    out["cobertura_360"] = sum(e["id"] in ff for e in ev) / len(ev)
    return out


def season_table() -> pd.DataFrame:
    ms = matches()
    summ = pd.DataFrame([match_summary(m) for m in ms["match_id"]])
    return ms.merge(summ, on="match_id")


if __name__ == "__main__":
    from pathlib import Path
    t = season_table()
    out = Path(__file__).resolve().parents[1] / "data" / "processed" / "jogos.csv"
    t.round(4).to_csv(out, index=False)
    print(t[["date", "opponent", "venue", "goals_for", "goals_against", "posse", "np_xg", "opp_np_xg",
             "ppda", "field_tilt", "formation", "opp_formation", "cobertura_360"]].round(2).to_string())
