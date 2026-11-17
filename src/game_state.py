"""Etapa 5: o Leverkusen de acordo com o placar (vencendo, empatando ou perdendo)."""
from __future__ import annotations

from collections import Counter, defaultdict

import numpy as np
import pandas as pd

from src.data import TEAM, events

STATES = ["Perdendo", "Empatando", "Vencendo"]


def label_states(match_id: int) -> list[tuple[dict, str, int, int]]:
    """Cada evento (exceto pênaltis de desempate) com o placar do Leverkusen ANTES do evento."""
    gf = ga = 0
    out = []
    for e in events(match_id):
        if e["period"] > 4:
            continue
        diff = gf - ga
        out.append((e, STATES[1 + int(np.sign(diff))], gf, ga))
        t, team = e["type"]["name"], e["team"]["name"]
        if t == "Shot" and e["shot"]["outcome"]["name"] == "Goal":
            gf, ga = (gf + 1, ga) if team == TEAM else (gf, ga + 1)
        elif t == "Own Goal For":
            gf, ga = (gf + 1, ga) if team == TEAM else (gf, ga + 1)
    return out


def state_summary(match_ids) -> pd.DataFrame:
    """Minutos, posse, xG por 90 e PPDA do Leverkusen em cada estado do placar."""
    dur, poss = Counter(), defaultdict(Counter)
    xg_for, xg_ag = Counter(), Counter()
    opp_pass, def_act = Counter(), Counter()
    from src.without_ball import _t
    for mid in match_ids:
        lab = label_states(mid)
        for i, (e, st, _, _) in enumerate(lab):
            # tempo até o próximo evento do mesmo período (cobre o jogo inteiro, sem buracos)
            nxt = lab[i + 1][0] if i + 1 < len(lab) else None
            d = (_t(nxt) - _t(e)) if nxt is not None and nxt["period"] == e["period"] else 0
            d = min(max(d, 0), 120)
            dur[st] += d
            poss[st][e["possession_team"]["name"] == TEAM] += d
            t, mine = e["type"]["name"], e["team"]["name"] == TEAM
            if t == "Shot" and e["shot"]["type"]["name"] != "Penalty":
                (xg_for if mine else xg_ag)[st] += e["shot"]["statsbomb_xg"]
            if not mine and t == "Pass" and e["location"][0] <= 72:
                opp_pass[st] += 1
            if mine and e.get("location") and e["location"][0] >= 48 and (
                    t in ("Interception", "Foul Committed", "Dribbled Past")
                    or (t == "Duel" and e["duel"]["type"]["name"] == "Tackle")):
                def_act[st] += 1
    rows = []
    for st in STATES:
        mins = dur[st] / 60
        rows.append({"estado": st, "minutos": mins,
                     "posse": poss[st][True] / max(poss[st][True] + poss[st][False], 1),
                     "xg_p90": xg_for[st] / mins * 90 if mins else np.nan,
                     "xg_contra_p90": xg_ag[st] / mins * 90 if mins else np.nan,
                     "ppda": opp_pass[st] / max(def_act[st], 1)})
    return pd.DataFrame(rows).set_index("estado")


def late_goals(match_ids, from_minute: int = 85) -> pd.DataFrame:
    """Resultado no minuto `from_minute` x resultado final e pontos ganhos com gols tardios."""
    pts = lambda gf, ga: 3 if gf > ga else (1 if gf == ga else 0)
    rows = []
    for mid in match_ids:
        labeled = label_states(mid)
        before = [x for x in labeled if x[0]["period"] == 2 and x[0]["minute"] < from_minute] or labeled
        _, _, gf85, ga85 = before[-1]
        late_for = sum(1 for e, *_ in labeled if e["period"] == 2 and e["minute"] >= from_minute and (
            (e["type"]["name"] == "Shot" and e["shot"]["outcome"]["name"] == "Goal" and e["team"]["name"] == TEAM)
            or (e["type"]["name"] == "Own Goal For" and e["team"]["name"] == TEAM)))
        e_last, _, gf, ga = labeled[-1]
        rows.append({"match_id": mid, "placar_85": f"{gf85}x{ga85}", "pontos_85": pts(gf85, ga85),
                     "gols_apos_85": late_for, "pontos_finais": None})
    return pd.DataFrame(rows)
