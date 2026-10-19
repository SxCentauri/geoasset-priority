from __future__ import annotations

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from .config import IMAGES

COLORS = {"Tinggi": "#d62828", "Sedang": "#f77f00", "Rendah": "#2a9d8f"}


def priority_map(scored: gpd.GeoDataFrame, zones: gpd.GeoDataFrame, path=None):
    path = path or IMAGES / "priority_map.png"
    IMAGES.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 7.2), dpi=140)
    zones.plot(ax=ax, column="rata_risiko", cmap="Blues", alpha=0.55,
               edgecolor="#6b7280", linewidth=0.8, legend=True,
               legend_kwds={"label": "Rata-rata skor risiko zona", "shrink": 0.6})
    for _, z in zones.iterrows():
        c = z.geometry.centroid
        ax.annotate(z["zone"], (c.x, c.y), ha="center", va="center", fontsize=8, color="#374151", alpha=0.8)
    for pr, col in COLORS.items():
        sub = scored[scored.priority == pr]
        sub[sub.geom_type == "LineString"].plot(ax=ax, color=col, linewidth=2.2, zorder=3)
        sub[sub.geom_type == "Point"].plot(ax=ax, color=col, markersize=14, zorder=4,
                                           edgecolor="white", linewidth=0.4)
    handles = [Line2D([0], [0], color=c, lw=3, label=f"Prioritas {p}") for p, c in COLORS.items()]
    ax.legend(handles=handles, loc="lower left", frameon=True)
    ax.set_title("Peta Prioritas Pemeliharaan Aset (data sintetis)", fontsize=13, weight="bold")
    ax.set_xlabel("Bujur (°)"); ax.set_ylabel("Lintang (°)")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path


def charts(scored: gpd.GeoDataFrame, path=None):
    path = path or IMAGES / "summary_charts.png"
    fig, axes = plt.subplots(1, 2, figsize=(11, 4), dpi=140)
    ct = scored.groupby(["asset_type", "priority"]).size().unstack(fill_value=0)
    ct = ct.reindex(columns=["Tinggi", "Sedang", "Rendah"], fill_value=0)
    ct.plot.bar(ax=axes[0], stacked=True, color=[COLORS[c] for c in ct.columns], rot=0)
    axes[0].set_title("Jumlah aset per tipe & prioritas"); axes[0].set_xlabel("")
    axes[1].hist(scored["risk_score"], bins=20, color="#264653", edgecolor="white")
    axes[1].set_title("Distribusi skor risiko"); axes[1].set_xlabel("Skor risiko (0-100)")
    fig.tight_layout(); fig.savefig(path); plt.close(fig)
    return path
