import os
from pathlib import Path

import geopandas as gpd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
URL = os.getenv("DATABASE_URL", "postgresql://geoasset:geoasset@localhost:5432/geoasset")

gdf = gpd.read_file(ROOT / "outputs" / "assets_scored.geojson")
cols = ["asset_id", "asset_type", "subtype", "condition", "install_year", "umur", "f_kondisi",
        "f_umur", "f_kritis", "risk_score", "priority", "quantity", "unit", "est_cost_idr", "geometry"]
gdf = gdf[cols].rename_geometry("geom")

engine = create_engine(URL)
with engine.begin() as conn:
    conn.execute(text("TRUNCATE assets_scored"))
gdf.to_postgis("assets_scored", engine, if_exists="append", index=False)
print(f"{len(gdf)} baris dimuat ke assets_scored")
