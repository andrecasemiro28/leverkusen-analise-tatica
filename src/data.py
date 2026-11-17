"""Download (com cache) e organização dos dados do Bayer Leverkusen 2023/24 (StatsBomb Open Data)."""
from __future__ import annotations

import json
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd

BASE_URL = "https://raw.githubusercontent.com/statsbomb/open-data/master/data"
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TEAM = "Bayer Leverkusen"
COMPETITION_ID, SEASON_ID = 9, 281  # 1. Bundesliga 2023/2024

# Classificação final da Bundesliga 2023/24 (para separar adversários fortes e fracos)
FINAL_TABLE = {
    "Bayer Leverkusen": 1, "VfB Stuttgart": 2, "Bayern Munich": 3, "RB Leipzig": 4,
    "Borussia Dortmund": 5, "Eintracht Frankfurt": 6, "Hoffenheim": 7, "FC Heidenheim": 8,
    "Werder Bremen": 9, "Freiburg": 10, "Augsburg": 11, "Wolfsburg": 12, "FSV Mainz 05": 13,
    "Borussia Mönchengladbach": 14, "Union Berlin": 15, "Bochum": 16, "FC Köln": 17, "Darmstadt 98": 18,
}


def _get(rel: str):
    local = RAW / rel
    if local.exists():
        return json.loads(local.read_text(encoding="utf-8"))
    local.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(f"{BASE_URL}/{rel}", timeout=120) as r:
            data = r.read()
    except urllib.error.HTTPError:
        return None
    local.write_bytes(data)
    return json.loads(data)


def matches() -> pd.DataFrame:
    """Uma linha por jogo, do ponto de vista do Leverkusen."""
    rows = []
    for m in _get(f"matches/{COMPETITION_ID}/{SEASON_ID}.json"):
        home = m["home_team"]["home_team_name"] == TEAM
        opp = m["away_team"]["away_team_name"] if home else m["home_team"]["home_team_name"]
        gf, ga = (m["home_score"], m["away_score"]) if home else (m["away_score"], m["home_score"])
        rows.append(dict(
            match_id=m["match_id"], date=pd.to_datetime(m["match_date"]), matchweek=m["match_week"],
            opponent=opp, venue="Casa" if home else "Fora", goals_for=gf, goals_against=ga,
            result="V" if gf > ga else ("E" if gf == ga else "D"),
            opp_rank=FINAL_TABLE.get(opp),
        ))
    df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    df["opp_level"] = pd.cut(df["opp_rank"], [0, 6, 12, 18], labels=["Top 6", "Meio", "Parte de baixo"])
    return df


def events(match_id: int) -> list[dict]:
    return _get(f"events/{match_id}.json")


def three_sixty(match_id: int) -> dict[str, dict]:
    """Freeze frames 360 indexados pelo id do evento (vazio se não houver)."""
    ff = _get(f"three-sixty/{match_id}.json") or []
    return {f["event_uuid"]: f for f in ff}


def download_all(workers: int = 8) -> pd.DataFrame:
    ms = matches()
    with ThreadPoolExecutor(workers) as pool:
        list(pool.map(lambda mid: (events(mid), three_sixty(mid)), ms["match_id"]))
    return ms


if __name__ == "__main__":
    ms = download_all()
    print(ms.to_string())


def lineups(match_id: int) -> dict[int, str]:
    """id do jogador -> nome curto (apelido quando existe)."""
    out = {}
    for team in _get(f"lineups/{match_id}.json"):
        for p in team["lineup"]:
            out[p["player_id"]] = p.get("player_nickname") or p["player_name"]
    return out
