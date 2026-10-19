from __future__ import annotations

import re

import geopandas as gpd
import pandas as pd
from shapely import wkt as shapely_wkt
from shapely.geometry import box

from .config import (ASSET_TYPES, CRS_GEO, DATA_PROCESSED, DATA_RAW,
                     REFERENCE_YEAR, STUDY_BBOX)

MIN_YEAR = 1950


def normalize_asset_type(value) -> str:
    """' Lampu PJU ' / 'Gorong-Gorong' -> 'lampu_pju' / 'gorong_gorong'."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = re.sub(r"[\s\-]+", "_", str(value).strip().lower())
    return s


def _parse_geom(w):
    if w is None or (isinstance(w, float) and pd.isna(w)) or str(w).strip() == "":
        return None, "geometri kosong"
    try:
        g = shapely_wkt.loads(str(w))
    except Exception:
        return None, "WKT tidak valid"
    if g.is_empty or not g.is_valid:
        return None, "geometri tidak valid"
    return g, None


def validate(df: pd.DataFrame) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    """Validasi dan bersihkan data mentah. Mengembalikan (bersih, ditolak)."""
    df = df.copy()
    df["asset_type"] = df["asset_type"].map(normalize_asset_type)
    study_area = box(*STUDY_BBOX)

    reasons: list[str | None] = []
    geoms = []
    seen: set[str] = set()

    for _, r in df.iterrows():
        reason = None
        g, err = _parse_geom(r["wkt"])
        if err:
            reason = err
        elif r["asset_type"] not in ASSET_TYPES:
            reason = f"tipe aset tidak dikenal: {r['asset_type']!r}"
        elif not study_area.contains(g):
            reason = "di luar wilayah studi (cek urutan lon/lat)"
        elif r["asset_type"] != "fasilitas_kritis":
            cond, yr = r["condition"], r["install_year"]
            if pd.isna(cond) or not 1 <= cond <= 5:
                reason = "skor kondisi di luar rentang 1-5"
            elif pd.isna(yr) or not MIN_YEAR <= yr <= REFERENCE_YEAR:
                reason = f"tahun pasang tidak wajar (harus {MIN_YEAR}-{REFERENCE_YEAR})"
        if reason is None:
            if r["asset_id"] in seen:
                reason = "asset_id duplikat"
            else:
                seen.add(r["asset_id"])
        reasons.append(reason)
        geoms.append(g)

    df["geometry"] = geoms
    df["reject_reason"] = reasons
    bad = df[df["reject_reason"].notna()].drop(columns=["geometry"])
    good = df[df["reject_reason"].isna()].drop(columns=["reject_reason", "wkt"])

    gdf = gpd.GeoDataFrame(good, geometry="geometry", crs=CRS_GEO)
    gdf["condition"] = gdf["condition"].astype("Int64")
    gdf["install_year"] = gdf["install_year"].astype("Int64")
    return gdf.reset_index(drop=True), bad.reset_index(drop=True)


def run(raw_path=None) -> tuple[gpd.GeoDataFrame, pd.DataFrame]:
    raw_path = raw_path or DATA_RAW / "survey_raw.csv"
    raw = pd.read_csv(raw_path)
    clean, rejected = validate(raw)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    clean.to_file(DATA_PROCESSED / "assets_clean.geojson", driver="GeoJSON")
    clean.to_file(DATA_PROCESSED / "assets_clean.gpkg", driver="GPKG", layer="assets")
    rejected.to_csv(DATA_PROCESSED / "rejected.csv", index=False)

    print(f"[etl] masuk={len(raw)} bersih={len(clean)} ditolak={len(rejected)}")
    if len(rejected):
        print(rejected["reject_reason"].value_counts().to_string())
    return clean, rejected


if __name__ == "__main__":
    run()
