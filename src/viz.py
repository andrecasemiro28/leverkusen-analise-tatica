"""Gráficos do projeto (paleta sóbria: vermelho Leverkusen como destaque + cinza)."""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ACCENT, MUTED, TEXT, SUB, BG = "#c8102e", "#9aa3ad", "#1f2328", "#57606a", "#f8f7f4"


def _style(ax, title, subtitle=None):
    ax.set_title(title, loc="left", size=14, weight="bold", color=TEXT, pad=24 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, size=10, color=SUB)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)


def season_xg(t: pd.DataFrame, save=None):
    """xG a favor e contra jogo a jogo, com média móvel de 5 jogos."""
    fig, ax = plt.subplots(figsize=(11, 5), facecolor=BG)
    ax.set_facecolor(BG)
    x = np.arange(1, len(t) + 1)
    ax.bar(x - 0.2, t["np_xg"], width=0.4, color=ACCENT, alpha=0.35, label="xG a favor (jogo)")
    ax.bar(x + 0.2, t["opp_np_xg"], width=0.4, color=MUTED, alpha=0.45, label="xG contra (jogo)")
    ax.plot(x, t["np_xg"].rolling(5, min_periods=1).mean(), color=ACCENT, lw=2.5, label="xG a favor (média 5 jogos)")
    ax.plot(x, t["opp_np_xg"].rolling(5, min_periods=1).mean(), color=SUB, lw=2.5, label="xG contra (média 5 jogos)")
    for xi, (r, o) in enumerate(zip(t["result"], t["opponent"]), start=1):
        if r == "E":
            ax.text(xi, -0.28, "E", ha="center", size=8.5, color=SUB, weight="bold")
    ax.set_xticks(x, [f"{i}" for i in t["matchweek"]], size=8.5)
    ax.set_xlabel("Rodada (E = empate; todos os outros jogos foram vitórias)", color=SUB)
    ax.set_ylabel("xG sem pênaltis", color=TEXT)
    ax.set_ylim(-0.4, max(t["np_xg"].max(), t["opp_np_xg"].max()) * 1.15)
    ax.axhline(0, color="#c3c8ce", lw=0.8)
    ax.legend(frameon=False, ncol=2, fontsize=9, loc="upper right")
    _style(ax, "Leverkusen 2023/24: 34 jogos, 0 derrotas",
           f"xG médio por jogo: {t['np_xg'].mean():.2f} a favor x {t['opp_np_xg'].mean():.2f} contra · Dados: StatsBomb Open Data")
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def draw_pitch(ax, color="#b9bec5", lw=1.1):
    """Campo inteiro horizontal (coordenadas StatsBomb 120 x 80, ataque para a direita)."""
    kw = dict(color=color, lw=lw, zorder=1)
    ax.plot([0, 120, 120, 0, 0], [0, 0, 80, 80, 0], **kw)
    ax.plot([60, 60], [0, 80], **kw)
    for x0, x1 in ((0, 18), (120, 102)):
        ax.plot([x0, x1, x1, x0], [18, 18, 62, 62], **kw)
    for x0, x1 in ((0, 6), (120, 114)):
        ax.plot([x0, x1, x1, x0], [30, 30, 50, 50], **kw)
    t = np.linspace(0, 2 * np.pi, 200)
    ax.plot(60 + 10 * np.cos(t), 40 + 10 * np.sin(t), **kw)
    ax.set_xlim(-2, 122); ax.set_ylim(82, -2)   # y invertido: lado esquerdo do ataque em cima
    ax.set_aspect("equal"); ax.axis("off")


def pass_networks(nets: dict, highlight: str | None = None, save=None):
    """Redes de passe lado a lado. nets = {titulo: (nodes, edges)}."""
    fig, axes = plt.subplots(1, len(nets), figsize=(7 * len(nets), 5.6), facecolor=BG)
    max_e = max(e["passes_pg"].max() for _, e in nets.values())
    max_t = max(n["touches_pg"].max() for n, _ in nets.values())
    for ax, (title, (nodes, edges)) in zip(np.atleast_1d(axes), nets.items()):
        ax.set_facecolor(BG); draw_pitch(ax)
        pos = nodes.set_index("player_id")
        for _, r in edges.iterrows():
            a, b = pos.loc[r["a"]], pos.loc[r["b"]]
            ax.plot([a.x, b.x], [a.y, b.y], color=SUB, lw=0.5 + 6 * r["passes_pg"] / max_e,
                    alpha=0.25 + 0.55 * r["passes_pg"] / max_e, zorder=2, solid_capstyle="round")
        placed = []
        for _, r in nodes.sort_values("touches_pg", ascending=False).iterrows():
            hl = highlight and highlight in r["name"]
            ax.scatter(r.x, r.y, s=60 + 420 * r["touches_pg"] / max_t, color=ACCENT if hl else "white",
                       edgecolor=ACCENT if hl else TEXT, lw=1.5, zorder=3)
            # rótulo abaixo do nó; se colidir com outro rótulo, tenta acima, à direita e à esquerda
            for dx, dy, ha, va in ((0, 3.6, "center", "top"), (0, -3.6, "center", "bottom"),
                                   (3.2, 0, "left", "center"), (-3.2, 0, "right", "center")):
                lx, ly = r.x + dx, r.y + dy
                if all(abs(lx - px) > 9 or abs(ly - py) > 3.2 for px, py in placed):
                    break
            placed.append((lx, ly))
            ax.text(lx, ly, r["name"], ha=ha, va=va, size=8.5, color=ACCENT if hl else TEXT, zorder=4,
                    weight="bold" if hl else "normal",
                    bbox=dict(facecolor=BG, edgecolor="none", alpha=0.75, pad=0.6))
        ax.set_title(title, size=12.5, weight="bold", color=TEXT, loc="left")
    fig.text(0.01, 1.04, "Redes de passe do Leverkusen: com e sem a bola", size=15, weight="bold", color=TEXT)
    fig.text(0.01, 0.995, "Posição média nas ações com bola · espessura = passes certos por jogo entre a dupla · "
             "círculo = participação · ataque para a direita", size=9.5, color=SUB)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def style_comparison(rows: pd.DataFrame, labels: tuple[str, str], save=None):
    """Comparação de indicadores entre dois grupos de jogos (barras horizontais pareadas)."""
    fig, axes = plt.subplots(len(rows), 1, figsize=(8.5, 0.85 * len(rows) + 1.2), facecolor=BG, sharex=False)
    for ax, (_, r) in zip(axes, rows.iterrows()):
        ax.set_facecolor(BG)
        vals = [r[labels[0]], r[labels[1]]]
        ax.barh([1, 0], vals, color=[MUTED, ACCENT], height=0.7)
        m = max(vals)
        for y, v in zip([1, 0], vals):
            ax.text(v + m * 0.02, y, r["fmt"].format(v), va="center", size=9.5, color=TEXT)
        ax.set_xlim(0, m * 1.25); ax.set_yticks([]); ax.set_xticks([])
        ax.text(-0.01, 0.5, r["metrica"], transform=ax.transAxes, ha="right", va="center", size=10, color=TEXT)
        for s in ("top", "right", "bottom"):
            ax.spines[s].set_visible(False)
    fig.text(0.01, 1.0, "Como o Leverkusen atacava em cada cenário", size=14, weight="bold", color=TEXT)
    fig.text(0.01, 0.965, f"■ {labels[0]}", color=SUB, size=10, weight="bold")
    fig.text(0.38, 0.965, f"■ {labels[1]}", color=ACCENT, size=10, weight="bold")
    fig.subplots_adjust(left=0.36, right=0.97, top=0.93, bottom=0.02, hspace=0.35)
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def progressive_maps(maps: dict, player: str, stats: dict, save=None):
    """Passes progressivos de um jogador em cada grupo de jogos."""
    fig, axes = plt.subplots(1, len(maps), figsize=(7 * len(maps), 5.4), facecolor=BG)
    for ax, (title, lst) in zip(np.atleast_1d(axes), maps.items()):
        ax.set_facecolor(BG); draw_pitch(ax)
        for s, e in lst:
            ax.annotate("", xy=(e[0], e[1]), xytext=(s[0], s[1]),
                        arrowprops=dict(arrowstyle="-|>", color=ACCENT, lw=1.1, alpha=0.75, mutation_scale=9), zorder=2)
        ax.set_title(f"{title}\n{stats[title]}", size=11.5, color=TEXT, loc="left", weight="bold")
    fig.text(0.01, 1.11, f"{player}: passes progressivos", size=15, weight="bold", color=TEXT)
    fig.text(0.01, 1.065, "Passes certos que aproximam a bola pelo menos 25% do gol adversário · ataque para a direita",
             size=9.5, color=SUB)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def recovery_zones(groups: dict, save=None, nx: int = 6, ny: int = 3):
    """% das recuperações de bola em cada zona do campo (6 faixas x 3 corredores)."""
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("lev", [BG, ACCENT])
    fig, axes = plt.subplots(1, len(groups), figsize=(7 * len(groups), 5.4), facecolor=BG)
    vmax = 0
    hists = {}
    for k, d in groups.items():
        H, xe, ye = np.histogram2d(d["x"], d["y"], bins=[np.linspace(0, 120, nx + 1), [0, 18, 62, 80]])
        hists[k] = (H / H.sum() * 100, xe, ye); vmax = max(vmax, (H / H.sum() * 100).max())
    for ax, (k, d) in zip(np.atleast_1d(axes), groups.items()):
        ax.set_facecolor(BG)
        H, xe, ye = hists[k]
        ax.pcolormesh(xe, ye, H.T, cmap=cmap, vmin=0, vmax=vmax, zorder=0)
        for i in range(nx):
            for j in range(ny):
                v = H[i, j]
                ax.text((xe[i] + xe[i + 1]) / 2, (ye[j] + ye[j + 1]) / 2, f"{v:.0f}%", ha="center", va="center",
                        size=10, color="white" if v > vmax * 0.55 else TEXT, weight="bold", zorder=3)
        draw_pitch(ax)
        h = d["x"].mean()
        ax.plot([h, h], [0, 80], color=TEXT, lw=1.8, ls="--", zorder=4)
        ax.text(h + 1, 81.5, f"altura média: {h * 0.9144:.0f} m", size=9, color=TEXT, va="top", zorder=4)
        att = (d["x"] >= 80).mean() * 100
        ax.set_title(f"{k}\n{len(d) / d['match_id'].nunique():.0f} recuperações por jogo · {att:.0f}% no terço final",
                     size=11.5, color=TEXT, loc="left", weight="bold")
    fig.text(0.01, 1.11, "Onde o Leverkusen recuperava a bola", size=15, weight="bold", color=TEXT)
    fig.text(0.01, 1.065, "Recuperações, interceptações e desarmes vencidos · % por zona · ataque para a direita",
             size=9.5, color=SUB)
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def counterpress_bars(df: pd.DataFrame, save=None):
    """% das perdas recuperadas em até 5 s: Leverkusen x adversários por cenário."""
    fig, ax = plt.subplots(figsize=(8.5, 4.8), facecolor=BG)
    ax.set_facecolor(BG)
    x = np.arange(len(df))
    ax.bar(x - 0.19, df["Leverkusen"], width=0.36, color=ACCENT, label="Leverkusen")
    ax.bar(x + 0.19, df["Adversários"], width=0.36, color=MUTED, label="Adversários (mesmos jogos)")
    for xi, (a, b) in enumerate(zip(df["Leverkusen"], df["Adversários"])):
        ax.text(xi - 0.19, a + 0.4, f"{a:.1f}%", ha="center", size=10, color=TEXT, weight="bold")
        ax.text(xi + 0.19, b + 0.4, f"{b:.1f}%", ha="center", size=10, color=SUB)
    ax.set_xticks(x, df.index, size=10.5)
    ax.set_yticks([]); ax.spines["left"].set_visible(False)
    ax.legend(frameon=False, loc="upper left", fontsize=9.5)
    ax.set_ylim(0, df.values.max() * 1.3)
    _style(ax, "Contrapressão: % das perdas de bola recuperadas em até 5 segundos",
           "Perdas em jogo corrido · recuperação = desarme, interceptação ou bola recuperada após toque do adversário")
    fig.tight_layout()
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def defensive_line_fig(by_zone: pd.DataFrame, per_match: pd.DataFrame, save=None):
    """Altura da linha defensiva: (a) por zona da bola, menos x mais posse; (b) por jogo x posse."""
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(14, 5.6), facecolor=BG, gridspec_kw={"width_ratios": [1, 1.25]})
    for ax in (a1, a2):
        ax.set_facecolor(BG)
    x = np.arange(len(by_zone.columns))
    for i, (grp, col) in enumerate((("menos posse", MUTED), ("mais posse", ACCENT))):
        vals = by_zone.loc[grp].values
        a1.bar(x + (i - 0.5) * 0.38, vals, width=0.36, color=col, label=f"Jogos com {grp}")
        for xi, v in zip(x, vals):
            a1.text(xi + (i - 0.5) * 0.38, v + 1, f"{v:.0f} m", ha="center", size=9.5, color=TEXT)
    a1.set_xticks(x, [c.replace("bola no ", "Bola no\n") for c in by_zone.columns], size=10)
    a1.set_ylabel("Altura da linha (m do próprio gol)", color=TEXT)
    a1.legend(frameon=False, fontsize=9.5, loc="upper left")
    a1.set_ylim(0, by_zone.values.max() * 1.2)
    _style(a1, "Sem a bola: mesma zona, linha mais baixa", "Média dos 3 jogadores de linha mais recuados")

    top = per_match["opp_rank"] <= 6
    a2.scatter(per_match.loc[~top, "posse"] * 100, per_match.loc[~top, "linha_sem_bola"], s=55, color=MUTED, label="Demais adversários", zorder=3)
    a2.scatter(per_match.loc[top, "posse"] * 100, per_match.loc[top, "linha_sem_bola"], s=70, color=ACCENT, label="Top 6", zorder=3)
    for _, r in per_match[top | (per_match["linha_sem_bola"] > 48)].iterrows():
        a2.annotate(f"{r['opponent'].replace('Borussia Mönchengladbach', 'Gladbach')} ({r['venue'][0]})",
                    (r["posse"] * 100, r["linha_sem_bola"]), xytext=(5, 3), textcoords="offset points", size=8.5, color=SUB)
    b = np.polyfit(per_match["posse"] * 100, per_match["linha_sem_bola"], 1)
    xx = np.linspace(per_match["posse"].min() * 100, per_match["posse"].max() * 100, 10)
    a2.plot(xx, np.polyval(b, xx), color=TEXT, lw=1, ls="--")
    a2.set_xlabel("Posse de bola no jogo (%)", color=TEXT); a2.set_ylabel("Altura média da linha sem a bola (m)", color=TEXT)
    a2.legend(frameon=False, fontsize=9.5, loc="upper left")
    r = per_match["posse"].corr(per_match["linha_sem_bola"])
    _style(a2, "Quanto mais posse, mais alta a linha", f"Um ponto por jogo (31 jogos com 360) · correlação = {r:.2f} · C = casa, F = fora")
    fig.tight_layout(w_pad=4)
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig


def game_state_fig(ss: pd.DataFrame, late: pd.DataFrame, save=None):
    """(a) xG e pressão por estado do placar; (b) jogos em que gols após os 85' mudaram o resultado."""
    fig = plt.figure(figsize=(14, 5.8), facecolor=BG)
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 0.8, 1.25], wspace=0.45)
    a1, a2, a3 = (fig.add_subplot(gs[0, i]) for i in range(3))
    order = ["Perdendo", "Empatando", "Vencendo"]
    ss = ss.loc[order]
    x = np.arange(3)
    a1.set_facecolor(BG)
    a1.bar(x - 0.19, ss["xg_p90"], width=0.36, color=ACCENT, label="xG a favor")
    a1.bar(x + 0.19, ss["xg_contra_p90"], width=0.36, color=MUTED, label="xG contra")
    for xi, (a, b) in enumerate(zip(ss["xg_p90"], ss["xg_contra_p90"])):
        a1.text(xi - 0.19, a + 0.04, f"{a:.2f}", ha="center", size=9, color=TEXT)
        a1.text(xi + 0.19, b + 0.04, f"{b:.2f}", ha="center", size=9, color=SUB)
    a1.set_xticks(x, [f"{s}\n({m:.0f}% do tempo)" for s, m in zip(order, ss["minutos"] / ss["minutos"].sum() * 100)], size=8.5)
    a1.set_ylim(0, ss["xg_p90"].max() * 1.45)
    a1.set_yticks([]); a1.spines["left"].set_visible(False)
    a1.legend(frameon=False, fontsize=9, loc="upper center", ncol=2)
    _style(a1, "xG por 90 min", "por placar no momento")

    a2.set_facecolor(BG)
    a2.bar(x, ss["ppda"], color=[ACCENT, "#e07a8a", MUTED], width=0.6)
    for xi, v in enumerate(ss["ppda"]):
        a2.text(xi, v + 0.3, f"{v:.1f}", ha="center", size=10, color=TEXT, weight="bold")
    a2.set_xticks(x, order, size=9.5); a2.set_yticks([]); a2.spines["left"].set_visible(False)
    _style(a2, "PPDA", "menor = mais pressão")

    a3.set_facecolor(BG); a3.axis("off")
    d = late[late["pontos_ganhos_tarde"] > 0].sort_values("pontos_ganhos_tarde", ascending=False)
    _style(a3, f"Gols após os 85': +{int(late['pontos_ganhos_tarde'].sum())} pontos",
           f"{int(late['gols_apos_85'].sum())} gols nos minutos finais · jogos em que eles mudaram o resultado")
    for i, (_, r) in enumerate(d.iterrows()):
        y = 0.86 - i * 0.17
        a3.text(0.0, y, f"{r['opponent']} ({r['venue'].lower()})", size=11, color=TEXT, weight="bold", transform=a3.transAxes)
        a3.text(0.0, y - 0.07, f"{r['placar_85']} aos 85'  →  {r['goals_for']}x{r['goals_against']} no final",
                size=10, color=SUB, transform=a3.transAxes)
        a3.text(0.98, y - 0.03, f"+{int(r['pontos_ganhos_tarde'])} pt", size=13, color=ACCENT, weight="bold",
                ha="right", transform=a3.transAxes)
    fig.text(0.01, 1.04, "Leverkusen de acordo com o placar", size=15, weight="bold", color=TEXT)
    if save:
        fig.savefig(save, dpi=160, bbox_inches="tight", facecolor=BG)
    return fig
