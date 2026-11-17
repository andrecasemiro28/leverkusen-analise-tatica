"""Etapa 3: o Leverkusen sem a bola. Contrapressão e onde o time recupera a bola."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data import TEAM, events

OPEN_PLAY = {"Regular Play", "From Counter"}


def _t(e) -> float:
    """Tempo do evento em segundos, contínuo dentro do período."""
    h, m, s = e["timestamp"].split(":")
    return e["period"] * 10_000 + int(h) * 3600 + int(m) * 60 + float(s)


def _possessions(ev):
    """Lista ordenada de posses: (id, time, padrão, tempo inicial, último evento com local do time em posse)."""
    poss = {}
    for e in ev:
        if e["period"] > 4:
            continue
        p = poss.setdefault(e["possession"], {"team": e["possession_team"]["name"], "pattern": e["play_pattern"]["name"],
                                              "t0": _t(e), "last_loc": None, "period": e["period"]})
        if e["team"]["name"] == p["team"] and e.get("location"):
            p["last_loc"] = e["location"]
    return [poss[k] for k in sorted(poss)]


def _wins_ball(e) -> bool:
    t = e["type"]["name"]
    return ((t == "Ball Recovery" and not e.get("ball_recovery", {}).get("recovery_failure"))
            or (t == "Interception" and e["interception"]["outcome"]["name"] in ("Won", "Success In Play", "Success Out"))
            or (t == "Duel" and e["duel"]["type"]["name"] == "Tackle"
                and e["duel"].get("outcome", {}).get("name") in ("Won", "Success In Play", "Success Out")))


def _is_turnover(e) -> bool:
    """Perda de bola em jogo corrido (sem contar bola para fora, impedimento ou finalização)."""
    t = e["type"]["name"]
    if t == "Pass":
        p = e["pass"]
        return (p.get("outcome", {}).get("name") == "Incomplete"
                and p.get("type", {}).get("name") not in ("Corner", "Free Kick", "Throw-in", "Goal Kick", "Kick Off"))
    if t == "Dribble":
        return e["dribble"]["outcome"]["name"] == "Incomplete"
    return t in ("Dispossessed", "Miscontrol")


def counterpress(match_id: int, team: str = TEAM, window: float = 5.0) -> pd.DataFrame:
    """Uma linha por perda de bola em jogo corrido do `team`.

    Recuperou em `window` s: o time ganha a bola de volta (recuperação, interceptação ou desarme vencido)
    em até `window` segundos, depois de o adversário tocar na bola, sem paralisação no meio.
    Também conta quantas pressões o time fez nesse intervalo (contrapressão).
    """
    ev = [e for e in events(match_id) if e["period"] <= 4]
    rows = []
    for i, e in enumerate(ev):
        if e["team"]["name"] != team or not _is_turnover(e):
            continue
        t0, opp_touched, regained_at, n_press = _t(e), False, None, 0
        for f in ev[i + 1:]:
            dt = _t(f) - t0
            if dt > window:
                break
            if f["type"]["name"] in ("Foul Committed", "Foul Won", "Half End", "Injury Stoppage", "Shot"):
                break
            if f["team"]["name"] != team:
                opp_touched = True
                continue
            if f["type"]["name"] == "Pressure":
                n_press += 1
            if opp_touched and _wins_ball(f):
                regained_at = dt
                break
        rows.append({"match_id": match_id, "team": team, "x_perda": e["location"][0], "y_perda": e["location"][1],
                     "segundos_ate_recuperar": regained_at, "recuperou_5s": regained_at is not None,
                     "pressoes_5s": n_press})
    return pd.DataFrame(rows)


def recoveries(match_id: int, team: str = TEAM) -> pd.DataFrame:
    """Onde o time ganhou a bola: recuperações, interceptações e desarmes vencidos."""
    rows = []
    for e in events(match_id):
        if e["team"]["name"] != team or e["period"] > 4 or not e.get("location"):
            continue
        t = e["type"]["name"]
        won = (
            (t == "Ball Recovery" and not e.get("ball_recovery", {}).get("recovery_failure"))
            or (t == "Interception" and e["interception"]["outcome"]["name"] in ("Won", "Success In Play", "Success Out"))
            or (t == "Duel" and e["duel"]["type"]["name"] == "Tackle"
                and e["duel"].get("outcome", {}).get("name") in ("Won", "Success In Play", "Success Out"))
        )
        if won:
            rows.append({"match_id": match_id, "team": team, "tipo": t, "x": e["location"][0], "y": e["location"][1]})
    return pd.DataFrame(rows)
