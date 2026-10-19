from __future__ import annotations

import geopandas as gpd
import numpy as np
import pandas as pd

from .config import (CRS_METRIC, DEFAULT_CONFIG, MAINTAINABLE_TYPES,
                     REFERENCE_YEAR, ScoringConfig)


def criticality(assets_m: gpd.GeoDataFrame, facilities_m: gpd.GeoDataFrame,
                cfg: ScoringConfig) -> pd.Series:
    result = pd.Series(0.0, index=assets_m.index)
    if facilities_m.empty:
        return result
    fac = facilities_m[["subtype", "geometry"]].copy()
    fac["w"] = fac["subtype"].map(cfg.critical_weights).fillna(0.0)
    fac["geometry"] = fac.geometry.buffer(cfg.critical_radius_m)
    joined = gpd.sjoin(assets_m[["geometry"]], fac[["w", "geometry"]],
                       how="inner", predicate="intersects")
    if joined.empty:
        return result
    best = joined.groupby(joined.index)["w"].max()
    result.loc[best.index] = best
    return result


def score_assets(clean: gpd.GeoDataFrame, cfg: ScoringConfig = DEFAULT_CONFIG,
                 ref_year: int = REFERENCE_YEAR) -> gpd.GeoDataFrame:
    """Hitung skor risiko, kelas prioritas, dimensi fisik, dan estimasi biaya."""
    assets = clean[clean.asset_type.isin(MAINTAINABLE_TYPES)].copy()
    facilities = clean[clean.asset_type == "fasilitas_kritis"].copy()

    a_m = assets.to_crs(CRS_METRIC)
    f_m = facilities.to_crs(CRS_METRIC)

    assets["umur"] = ref_year - assets["install_year"].astype(int)
    life = assets["asset_type"].map(cfg.design_life)
    assets["f_kondisi"] = (assets["condition"].astype(float) - 1) / 4
    assets["f_umur"] = np.minimum(assets["umur"] / life, 1.0)
    assets["f_kritis"] = criticality(a_m, f_m, cfg)

    base = (cfg.w_condition * assets["f_kondisi"]
            + cfg.w_age * assets["f_umur"]
            + cfg.w_criticality * assets["f_kritis"])
    assets["risk_score"] = (100 * assets["asset_type"].map(cfg.type_weight) * base).round(1)

    assets["priority"] = np.select(
        [assets.risk_score >= cfg.threshold_high, assets.risk_score >= cfg.threshold_medium],
        ["Tinggi", "Sedang"], default="Rendah")

    qty = np.where(assets.asset_type == "jalan", a_m.geometry.length, 1.0)
    assets["quantity"] = np.round(qty, 1)
    assets["unit"] = np.where(assets.asset_type == "jalan", "m", "titik")
    assets["est_cost_idr"] = (qty * assets["asset_type"].map(cfg.cost_per_unit)).round(-3).astype("int64")
    return assets.reset_index(drop=True)


def zone_grid(bbox, nx: int = 4, ny: int = 3) -> gpd.GeoDataFrame:
    from shapely.geometry import box
    lon0, lat0, lon1, lat1 = bbox
    xs = np.linspace(lon0, lon1, nx + 1)
    ys = np.linspace(lat0, lat1, ny + 1)
    cells, names = [], []
    for j in range(ny):
        for i in range(nx):
            cells.append(box(xs[i], ys[j], xs[i + 1], ys[j + 1]))
            names.append(f"Z{j * nx + i + 1:02d}")
    return gpd.GeoDataFrame({"zone": names}, geometry=cells, crs="EPSG:4326")


def summarize_by_zone(scored: gpd.GeoDataFrame, zones: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    pts = scored.copy()
    pts["geometry"] = pts.geometry.representative_point()
    joined = gpd.sjoin(pts, zones, how="left", predicate="intersects")
    joined = joined[~joined.index.duplicated(keep="first")]
    agg = joined.groupby("zone").agg(
        jumlah_aset=("asset_id", "count"),
        rata_risiko=("risk_score", "mean"),
        aset_prioritas_tinggi=("priority", lambda s: int((s == "Tinggi").sum())),
        total_biaya_idr=("est_cost_idr", "sum"),
    ).round(1)
    out = zones.merge(agg, left_on="zone", right_index=True, how="left").fillna(0)
    return out
