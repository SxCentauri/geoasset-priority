import geopandas as gpd
import pandas as pd
from shapely.geometry import LineString, Point

from geoasset.config import ScoringConfig
from geoasset.optimizer import select_within_budget
from geoasset.scoring import score_assets, zone_grid, summarize_by_zone


def _gdf(rows):
    return gpd.GeoDataFrame(pd.DataFrame(rows), geometry="geometry", crs="EPSG:4326")


def _lamp(i, cond, year, x=102.30, y=-3.82):
    return dict(asset_id=f"LT-{i}", asset_type="lampu_pju", subtype="led",
                condition=cond, install_year=year, geometry=Point(x, y))


def test_worse_condition_and_age_gives_higher_risk():
    g = _gdf([_lamp(1, 1, 2025), _lamp(2, 5, 2005)])
    s = score_assets(g).set_index("asset_id")
    assert s.loc["LT-2", "risk_score"] > s.loc["LT-1", "risk_score"]


def test_risk_is_between_0_and_100():
    g = _gdf([_lamp(1, 1, 2026), _lamp(2, 5, 1990)])
    s = score_assets(g)
    assert s.risk_score.between(0, 100).all()


def test_nearby_hospital_raises_criticality():
    near = _lamp(1, 3, 2015, 102.300, -3.82)
    far = _lamp(2, 3, 2015, 102.330, -3.80)
    hosp = dict(asset_id="FK-1", asset_type="fasilitas_kritis", subtype="rumah_sakit",
                condition=pd.NA, install_year=pd.NA, geometry=Point(102.3005, -3.82))
    s = score_assets(_gdf([near, far, hosp])).set_index("asset_id")
    assert s.loc["LT-1", "f_kritis"] == 1.0
    assert s.loc["LT-2", "f_kritis"] == 0.0
    assert s.loc["LT-1", "risk_score"] > s.loc["LT-2", "risk_score"]


def test_road_length_computed_in_meters():
    road = dict(asset_id="RD-1", asset_type="jalan", subtype="lokal", condition=3,
                install_year=2010, geometry=LineString([(102.30, -3.82), (102.31, -3.82)]))
    s = score_assets(_gdf([road]))
    assert 1050 < s.loc[0, "quantity"] < 1150 and s.loc[0, "unit"] == "m"
    assert abs(s.loc[0, "est_cost_idr"] - s.loc[0, "quantity"] * 450_000) < 100_000


def test_priority_thresholds():
    cfg = ScoringConfig()
    g = _gdf([_lamp(1, 5, 1990), _lamp(2, 1, 2026)])
    s = score_assets(g, cfg).set_index("asset_id")
    assert s.loc["LT-2", "priority"] == "Rendah"
    assert s.loc["LT-1", "priority"] in ("Sedang", "Tinggi")


def test_budget_selection_never_exceeds_budget():
    g = _gdf([_lamp(i, 1 + i % 5, 2000 + i) for i in range(30)])
    s = score_assets(g)
    plan = select_within_budget(s, budget_idr=40_000_000)
    assert plan.est_cost_idr.sum() <= 40_000_000
    assert plan["rank"].tolist() == list(range(1, len(plan) + 1))


def test_zone_summary_counts_all_assets():
    g = _gdf([_lamp(i, 3, 2010, 102.27 + 0.005 * i, -3.82) for i in range(10)])
    s = score_assets(g)
    z = summarize_by_zone(s, zone_grid((102.27, -3.86, 102.34, -3.78)))
    assert z["jumlah_aset"].sum() == 10
