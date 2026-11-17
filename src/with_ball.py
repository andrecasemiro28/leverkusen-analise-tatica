"""Etapa 2: o Leverkusen com a bola. Redes de passe, estilo de construção e o papel do Xhaka."""
from __future__ import annotations

from collections import Counter, defaultdict
from math import hypot

import numpy as np
import pandas as pd

from src.data import TEAM, events, lineups

GOAL = (120, 40)
SET_PIECES = {"Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"}


def _progressive(s, e) -> bool:
    d0, d1 = hypot(GOAL[0] - s[0], GOAL[1] - s[1]), hypot(GOAL[0] - e[0], GOAL[1] - e[1])
    return s[0] >= 40 and d1 <= 0.75 * d0


def player_minutes(ev: list[dict]) -> dict[int, float]:
    """Minutos de cada jogador do Leverkusen no jogo (titulares, substituições e expulsões)."""
    ev = [e for e in ev if e["period"] <= 4]
    end = max(e["minute"] + e["second"] / 60 for e in ev)
    on, off = {}, {}
    for e in ev:
        if e["team"]["name"] != TEAM:
            continue
        t = e["minute"] + e["second"] / 60
        if e["type"]["name"] == "Starting XI":
            for p in e["tactics"]["lineup"]:
                on[p["player"]["id"]] = 0.0
        elif e["type"]["name"] == "Substitution":
            off[e["player"]["id"]] = t
            on[e["substitution"]["replacement"]["id"]] = t
        elif e["type"]["name"] in ("Foul Committed", "Bad Behaviour"):
            card = (e.get("foul_committed") or e.get("bad_behaviour") or {}).get("card", {}).get("name")
            if card in ("Red Card", "Second Yellow"):
                off[e["player"]["id"]] = t
    return {p: max(off.get(p, end) - s, 0) for p, s in on.items()}


def pass_network(match_ids, n_players: int = 11, min_edge: float = 2.0):
    """Rede de passes agregada de um grupo de jogos.

    Nós: posição média de cada jogador nas ações com bola (passes dados e recebidos).
    Arestas: passes certos entre o par (nos dois sentidos), em média por jogo.
    """
    locs = defaultdict(list)
    edges = Counter()
    involvement = Counter()
    names = {}
    for mid in match_ids:
        names.update(lineups(mid))
        for e in events(mid):
            if e["team"]["name"] != TEAM or e["type"]["name"] != "Pass" or e["period"] > 4:
                continue
            p = e["pass"]
            if p.get("type", {}).get("name") in SET_PIECES or "outcome" in p or "recipient" not in p:
                continue
            a, b = e["player"]["id"], p["recipient"]["id"]
            locs[a].append(e["location"]); locs[b].append(p["end_location"])
            involvement[a] += 1; involvement[b] += 1
            edges[tuple(sorted((a, b)))] += 1
    top = [p for p, _ in involvement.most_common(n_players)]
    n = len(match_ids)
    nodes = pd.DataFrame([{
        "player_id": p, "name": names[p].split()[-1] if names[p].count(" ") else names[p],
        "x": np.mean([l[0] for l in locs[p]]), "y": np.mean([l[1] for l in locs[p]]),
        "touches_pg": involvement[p] / n,
    } for p in top])
    ed = pd.DataFrame([{"a": a, "b": b, "passes_pg": c / n} for (a, b), c in edges.items()
                       if a in top and b in top and c / n >= min_edge])
    return nodes, ed


def build_up_style(match_id: int) -> dict:
    """Indicadores de estilo de construção do Leverkusen em um jogo."""
    ev = [e for e in events(match_id) if e["period"] <= 4]
    mine = [e for e in ev if e["team"]["name"] == TEAM]
    passes = [e for e in mine if e["type"]["name"] == "Pass" and e["pass"].get("type", {}).get("name") not in SET_PIECES]
    ok = [p for p in passes if "outcome" not in p["pass"]]
    long_ = [p for p in passes if p["pass"]["length"] >= 35]           # ~32 m
    prog = [p for p in ok if _progressive(p["location"], p["pass"]["end_location"])]

    # posses do Leverkusen: nº de passes e ritmo
    poss = defaultdict(list)
    for e in ev:
        if e["possession_team"]["name"] == TEAM:
            poss[e["possession"]].append(e)
    shots, fast_xg, counter_xg, tot_xg, pass_per_poss, speeds = 0, 0.0, 0.0, 0.0, [], []
    for pid, pe in poss.items():
        n_pass = sum(1 for e in pe if e["type"]["name"] == "Pass" and e["team"]["name"] == TEAM)
        pass_per_poss.append(n_pass)
        sh = [e for e in pe if e["type"]["name"] == "Shot" and e["team"]["name"] == TEAM
              and e["shot"]["type"]["name"] != "Penalty"]
        if not sh:
            continue
        xg = sum(s["shot"]["statsbomb_xg"] for s in sh)
        tot_xg += xg; shots += len(sh)
        t0 = pe[0]["minute"] * 60 + pe[0]["second"]
        t1 = sh[-1]["minute"] * 60 + sh[-1]["second"]
        start_x = next((e["location"][0] for e in pe if e["team"]["name"] == TEAM and e.get("location")), None)
        if start_x is not None and t1 > t0:
            speeds.append((sh[-1]["location"][0] - start_x) / (t1 - t0))
        if t1 - t0 <= 15:
            fast_xg += xg
        if pe[0]["play_pattern"]["name"] == "From Counter":
            counter_xg += xg
    return {
        "match_id": match_id,
        "passes_por_posse": float(np.mean(pass_per_poss)),
        "pct_passes_longos": len(long_) / len(passes),
        "passes_progressivos": len(prog),
        "pct_progressivos": len(prog) / len(ok),
        "velocidade_ataque": float(np.median(speeds)) if speeds else np.nan,   # jardas/s até o chute
        "pct_xg_ataque_rapido": fast_xg / tot_xg if tot_xg else 0,           # posses de até 15 s
        "pct_xg_contra_ataque": counter_xg / tot_xg if tot_xg else 0,
        "xg_por_chute": tot_xg / shots if shots else 0,
    }


def player_profile(match_ids, player_name: str) -> dict:
    """Envolvimento de um jogador com a bola num grupo de jogos (por 90 minutos)."""
    mins, n_pass, n_ok, n_prog, n_long, team_pass, xs, ys, prog_list = 0, 0, 0, 0, 0, 0, [], [], []
    for mid in match_ids:
        ev = events(mid)
        names = lineups(mid)
        pid = next((k for k, v in names.items() if v == player_name), None)
        m = player_minutes(ev)
        if pid is None or pid not in m:
            continue
        mins += m[pid]
        for e in ev:
            if e["team"]["name"] != TEAM or e["type"]["name"] != "Pass":
                continue
            if e["pass"].get("type", {}).get("name") in SET_PIECES:
                continue
            team_pass += 1
            if e["player"]["id"] != pid:
                continue
            n_pass += 1
            xs.append(e["location"][0]); ys.append(e["location"][1])
            if "outcome" not in e["pass"]:
                n_ok += 1
                if _progressive(e["location"], e["pass"]["end_location"]):
                    n_prog += 1
                    prog_list.append((e["location"], e["pass"]["end_location"]))
            if e["pass"]["length"] >= 35:
                n_long += 1
    p90 = mins / 90 if mins else np.nan
    return {"jogador": player_name, "minutos": round(mins), "passes_p90": n_pass / p90,
            "pct_passes_do_time": n_pass / team_pass, "pct_certos": n_ok / n_pass if n_pass else np.nan,
            "progressivos_p90": n_prog / p90, "pct_longos": n_long / n_pass if n_pass else np.nan,
            "x_medio": float(np.mean(xs)) if xs else np.nan, "y_medio": float(np.mean(ys)) if ys else np.nan,
            "_progressivos": prog_list}
