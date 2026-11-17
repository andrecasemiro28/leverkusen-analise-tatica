"""Refaz o projeto inteiro: baixa os dados, calcula as métricas e gera todos os gráficos.

Uso:  python -m src.run_all
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src import viz
from src.data import download_all
from src.game_state import late_goals, state_summary
from src.metrics import season_table
from src.shape import defensive_line
from src.with_ball import build_up_style, pass_network, player_profile
from src.without_ball import counterpress, recoveries

ROOT = Path(__file__).resolve().parents[1]
P, F = ROOT / "data" / "processed", ROOT / "reports" / "figures"


def main():
    P.mkdir(parents=True, exist_ok=True); F.mkdir(parents=True, exist_ok=True)
    print("1/6 dados"); download_all()

    print("2/6 resumo por jogo")
    t = season_table()
    t = t.merge(pd.DataFrame([build_up_style(m) for m in t["match_id"]]), on="match_id")
    t.to_csv(P / "jogos.csv", index=False)
    viz.season_xg(t, save=F / "temporada_xg.png")
    low = list(t.nsmallest(7, "posse")["match_id"]); high = list(t.nlargest(7, "posse")["match_id"])

    print("3/6 com a bola")
    viz.pass_networks({"Jogos com MENOS posse (média 45%)": pass_network(low),
                       "Jogos com MAIS posse (média 74%)": pass_network(high)},
                      highlight="Xhaka", save=F / "redes_passe.png")
    gl, gh = t[t["match_id"].isin(low)].mean(numeric_only=True), t[t["match_id"].isin(high)].mean(numeric_only=True)
    L = ("Menos posse (7 jogos)", "Mais posse (7 jogos)")
    rows = pd.DataFrame([
        ("Passes por posse", gl.passes_por_posse, gh.passes_por_posse, "{:.1f}"),
        ("Velocidade até o chute (m/s)", gl.velocidade_ataque * 0.9144, gh.velocidade_ataque * 0.9144, "{:.1f}"),
        ("% de passes longos", gl.pct_passes_longos * 100, gh.pct_passes_longos * 100, "{:.1f}%"),
        ("Finalizações por jogo", gl.shots, gh.shots, "{:.1f}"),
        ("xG a favor por jogo", gl.np_xg, gh.np_xg, "{:.2f}"),
        ("xG contra por jogo", gl.opp_np_xg, gh.opp_np_xg, "{:.2f}"),
        ("PPDA (menor = mais pressão)", gl.ppda, gh.ppda, "{:.1f}"),
    ], columns=["metrica", L[0], L[1], "fmt"])
    viz.style_comparison(rows, L, save=F / "estilo_posse.png")
    pl, ph = player_profile(low, "Granit Xhaka"), player_profile(high, "Granit Xhaka")
    stats = {k: f"{p['passes_p90']:.0f} passes/90 · {p['progressivos_p90']:.1f} progressivos/90"
             for k, p in (("Jogos com MENOS posse", pl), ("Jogos com MAIS posse", ph))}
    viz.progressive_maps({"Jogos com MENOS posse": pl["_progressivos"], "Jogos com MAIS posse": ph["_progressivos"]},
                         "Granit Xhaka", stats, save=F / "xhaka_progressivos.png")

    print("4/6 sem a bola")
    cp = pd.concat([counterpress(m) for m in t["match_id"]])
    op = pd.concat([counterpress(m, team=o) for m, o in zip(t["match_id"], t["opponent"])])
    rec = pd.concat([recoveries(m) for m in t["match_id"]])
    cp.to_csv(P / "contrapressao.csv", index=False); op.to_csv(P / "contrapressao_adv.csv", index=False)
    rec.to_csv(P / "recuperacoes.csv", index=False)
    pct = lambda d: d["recuperou_5s"].mean() * 100
    viz.counterpress_bars(pd.DataFrame(
        {"Leverkusen": [pct(cp), pct(cp[cp.match_id.isin(low)]), pct(cp[cp.match_id.isin(high)])],
         "Adversários": [pct(op), pct(op[op.match_id.isin(low)]), pct(op[op.match_id.isin(high)])]},
        index=["Temporada (34 jogos)", "Jogos com menos posse", "Jogos com mais posse"]), save=F / "contrapressao.png")
    viz.recovery_zones({"Jogos com MENOS posse": rec[rec.match_id.isin(low)],
                        "Jogos com MAIS posse": rec[rec.match_id.isin(high)]}, save=F / "recuperacoes.png")

    print("5/6 linha defensiva (360)")
    ok = t[t["cobertura_360"] > 0.5]
    dl = pd.concat([defensive_line(m) for m in ok["match_id"]])
    dl.to_csv(P / "linha_defensiva.csv", index=False)
    dl["grupo"] = np.where(dl.match_id.isin(low), "menos posse", np.where(dl.match_id.isin(high), "mais posse", "outros"))
    dl["zona"] = pd.cut(dl["bola_m"], [0, 36.6, 73.2, 110], labels=["bola no nosso terço", "bola no meio", "bola no terço deles"])
    bz = dl[(~dl.com_bola) & (dl.grupo != "outros")].groupby(["grupo", "zona"], observed=True)["altura_m"].mean().unstack()
    pm = (dl[~dl.com_bola].groupby("match_id")["altura_m"].mean().rename("linha_sem_bola").to_frame()
          .join(dl[dl.com_bola].groupby("match_id")["altura_m"].mean().rename("linha_com_bola")).reset_index())
    pm.to_csv(P / "linha_por_jogo.csv", index=False)
    viz.defensive_line_fig(bz, t.merge(pm, on="match_id"), save=F / "linha_defensiva.png")

    print("6/6 placar")
    ss = state_summary(t["match_id"]); ss.to_csv(P / "estado_placar.csv")
    pts = {"V": 3, "E": 1, "D": 0}
    lg = late_goals(t["match_id"]).merge(t[["match_id", "opponent", "venue", "goals_for", "goals_against", "result"]], on="match_id")
    lg["pontos_finais"] = lg["result"].map(pts); lg["pontos_ganhos_tarde"] = lg["pontos_finais"] - lg["pontos_85"]
    lg.to_csv(P / "gols_tardios.csv", index=False)
    viz.game_state_fig(ss, lg, save=F / "placar.png")
    print("pronto")


if __name__ == "__main__":
    main()
