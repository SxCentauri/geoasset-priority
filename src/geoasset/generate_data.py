from __future__ import annotations

import numpy as np
import pandas as pd
from shapely.geometry import LineString, Point

from .config import DATA_RAW, STUDY_BBOX, REFERENCE_YEAR

SEED = 2026
SURVEYORS = ["Tim-A", "Tim-B", "Tim-C", "Tim-D"]


def _random_road(rng: np.random.Generator) -> LineString:
    lon_min, lat_min, lon_max, lat_max = STUDY_BBOX
    x = rng.uniform(lon_min + 0.005, lon_max - 0.005)
    y = rng.uniform(lat_min + 0.005, lat_max - 0.005)
    heading = rng.uniform(0, 2 * np.pi)
    pts = [(x, y)]
    for _ in range(rng.integers(3, 6)):
        heading += rng.normal(0, 0.35)
        step = rng.uniform(0.0018, 0.0035)  # +- 200-390 m
        x = float(np.clip(x + step * np.cos(heading), lon_min + 0.001, lon_max - 0.001))
        y = float(np.clip(y + step * np.sin(heading), lat_min + 0.001, lat_max - 0.001))
        pts.append((x, y))
    return LineString(pts)


def _condition_from_age(rng, age: int, life: int) -> int:
    base = 1 + 4 * min(age / life, 1.2) / 1.2
    return int(np.clip(round(base + rng.normal(0, 0.8)), 1, 5))


def generate(seed: int = SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows: list[dict] = []
    counters = {"jalan": 0, "lampu_pju": 0, "gorong_gorong": 0, "fasilitas_kritis": 0}

    def next_id(t: str, prefix: str) -> str:
        counters[t] += 1
        return f"{prefix}-{counters[t]:04d}"

    life = {"jalan": 15, "lampu_pju": 12, "gorong_gorong": 25}
    roads = [_random_road(rng) for _ in range(45)]

    for i, road in enumerate(roads):
        year = int(REFERENCE_YEAR - rng.integers(1, 22))
        age = REFERENCE_YEAR - year
        rows.append(dict(
            asset_id=next_id("jalan", "RD"), asset_type="jalan", subtype="lokal",
            name=f"Ruas Jalan {i + 1:02d}", wkt=road.wkt,
            condition=_condition_from_age(rng, age, life["jalan"]),
            install_year=year, last_inspection=f"2026-{rng.integers(1, 10):02d}-{rng.integers(1, 28):02d}",
            surveyor=rng.choice(SURVEYORS), notes=""))

        n_lamp = int(rng.integers(4, 9))
        for k in range(n_lamp):
            p = road.interpolate((k + 0.5) / n_lamp, normalized=True)
            year_l = int(REFERENCE_YEAR - rng.integers(1, 16))
            rows.append(dict(
                asset_id=next_id("lampu_pju", "LT"), asset_type="lampu_pju", subtype="led",
                name="", wkt=Point(p.x + rng.normal(0, 4e-5), p.y + rng.normal(0, 4e-5)).wkt,
                condition=_condition_from_age(rng, REFERENCE_YEAR - year_l, life["lampu_pju"]),
                install_year=year_l,
                last_inspection=f"2026-{rng.integers(1, 10):02d}-{rng.integers(1, 28):02d}",
                surveyor=rng.choice(SURVEYORS), notes=""))

        for _ in range(int(rng.integers(0, 3))):
            p = road.interpolate(rng.uniform(0.1, 0.9), normalized=True)
            year_g = int(REFERENCE_YEAR - rng.integers(2, 30))
            rows.append(dict(
                asset_id=next_id("gorong_gorong", "CV"), asset_type="gorong_gorong", subtype="beton",
                name="", wkt=Point(p.x + rng.normal(0, 3e-5), p.y + rng.normal(0, 3e-5)).wkt,
                condition=_condition_from_age(rng, REFERENCE_YEAR - year_g, life["gorong_gorong"]),
                install_year=year_g,
                last_inspection=f"2026-{rng.integers(1, 10):02d}-{rng.integers(1, 28):02d}",
                surveyor=rng.choice(SURVEYORS), notes=""))

    lon_min, lat_min, lon_max, lat_max = STUDY_BBOX
    for sub, n in (("rumah_sakit", 3), ("puskesmas", 5), ("sekolah", 17)):
        for j in range(n):
            rows.append(dict(
                asset_id=next_id("fasilitas_kritis", "FK"), asset_type="fasilitas_kritis", subtype=sub,
                name=f"{sub.replace('_', ' ').title()} {j + 1}",
                wkt=Point(rng.uniform(lon_min + 0.004, lon_max - 0.004),
                          rng.uniform(lat_min + 0.004, lat_max - 0.004)).wkt,
                condition=np.nan, install_year=np.nan, last_inspection="",
                surveyor="", notes="fasilitas rujukan"))

    df = pd.DataFrame(rows)
    return _inject_dirty_rows(df, rng)


def _inject_dirty_rows(df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Sisipkan kesalahan entri yang lazim terjadi pada survei lapangan."""
    lamp = df[df.asset_type == "lampu_pju"].index.to_list()
    jalan = df[df.asset_type == "jalan"].index.to_list()
    cv = df[df.asset_type == "gorong_gorong"].index.to_list()

    dirty = []
    for idx in lamp[:3]:
        dirty.append(df.loc[idx].copy())
    r = df.loc[lamp[10]].copy(); r["asset_id"] = "LT-X001"; r["wkt"] = ""; dirty.append(r)
    r = df.loc[cv[2]].copy(); r["asset_id"] = "CV-X002"; r["wkt"] = None; dirty.append(r)
    r = df.loc[lamp[11]].copy(); r["asset_id"] = "LT-X003"; r["wkt"] = "POINT (abc def)"; dirty.append(r)
    r = df.loc[lamp[12]].copy(); r["asset_id"] = "LT-X004"; r["wkt"] = "POINT (-3.81 102.30)"; dirty.append(r)
    r = df.loc[cv[3]].copy(); r["asset_id"] = "CV-X005"; r["wkt"] = "POINT (110.5 -6.2)"; dirty.append(r)
    r = df.loc[lamp[13]].copy(); r["asset_id"] = "LT-X006"; r["condition"] = 9; dirty.append(r)
    r = df.loc[jalan[4]].copy(); r["asset_id"] = "RD-X007"; r["condition"] = 0; dirty.append(r)
    r = df.loc[lamp[14]].copy(); r["asset_id"] = "LT-X008"; r["install_year"] = 2031; dirty.append(r)
    r = df.loc[cv[4]].copy(); r["asset_id"] = "CV-X009"; r["install_year"] = 1890; dirty.append(r)
    r = df.loc[lamp[15]].copy(); r["asset_id"] = "LT-X010"; r["asset_type"] = " Lampu PJU "; dirty.append(r)
    r = df.loc[cv[5]].copy(); r["asset_id"] = "CV-X011"; r["asset_type"] = "Gorong-Gorong"; dirty.append(r)

    out = pd.concat([df, pd.DataFrame(dirty)], ignore_index=True)
    return out.sample(frac=1, random_state=7).reset_index(drop=True)


def main() -> None:
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    df = generate()
    path = DATA_RAW / "survey_raw.csv"
    df.to_csv(path, index=False)
    print(f"[generate] {len(df)} baris -> {path}")


if __name__ == "__main__":
    main()
