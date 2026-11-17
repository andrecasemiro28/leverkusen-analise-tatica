"""Etapa 4: forma do time com os dados 360. Altura da linha defensiva do Leverkusen."""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data import TEAM, events, three_sixty

YD_TO_M = 0.9144


def defensive_line(match_id: int, min_visible: int = 8, n_back: int = 3) -> pd.DataFrame:
    """Altura da linha defensiva em cada evento com freeze frame.

    Altura = média da distância ao próprio gol dos `n_back` jogadores de linha mais recuados do Leverkusen
    (o time jogava com 3 zagueiros). Só usa lances com pelo menos `min_visible` jogadores de linha do
    Leverkusen visíveis, para a linha não "sumir" da câmera.
    """
    ff = three_sixty(match_id)
    rows = []
    for e in events(match_id):
        f = ff.get(e["id"])
        if f is None or e["period"] > 4 or not e.get("location"):
            continue
        lev_is_actor = e["team"]["name"] == TEAM
        xs = []
        for p in f["freeze_frame"]:
            same_team_as_actor = p["teammate"] or p.get("actor", False)
            is_lev = same_team_as_actor if lev_is_actor else not same_team_as_actor
            if not is_lev or p.get("keeper"):
                continue
            x = p["location"][0]
            xs.append(x if lev_is_actor else 120 - x)   # distância ao próprio gol, no referencial do Leverkusen
        if len(xs) < min_visible:
            continue
        ball_x = e["location"][0] if lev_is_actor else 120 - e["location"][0]
        rows.append({"match_id": match_id, "com_bola": lev_is_actor, "altura_m": np.mean(sorted(xs)[:n_back]) * YD_TO_M,
                     "bola_m": ball_x * YD_TO_M})
    return pd.DataFrame(rows)
