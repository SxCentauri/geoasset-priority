from __future__ import annotations

import argparse
import json

from . import etl, generate_data, optimizer, report, scoring
from .config import DEFAULT_CONFIG, OUTPUTS, STUDY_BBOX, WEB, DATA_RAW


def main(budget_idr: int = 2_000_000_000, regenerate: bool = True) -> dict:
    OUTPUTS.mkdir(parents=True, exist_ok=True)
    WEB.mkdir(parents=True, exist_ok=True)

    if regenerate or not (DATA_RAW / "survey_raw.csv").exists():
        generate_data.main()
    clean, rejected = etl.run()

    scored = scoring.score_assets(clean)
    zones = scoring.zone_grid(STUDY_BBOX)
    zone_sum = scoring.summarize_by_zone(scored, zones)
    plan = optimizer.select_within_budget(scored, budget_idr, min_risk=DEFAULT_CONFIG.threshold_medium)

    scored.to_file(OUTPUTS / "assets_scored.geojson", driver="GeoJSON")
    zone_sum.to_file(OUTPUTS / "zone_summary.geojson", driver="GeoJSON")
    zone_sum.drop(columns="geometry").to_csv(OUTPUTS / "zone_summary.csv", index=False)
    top = scored.sort_values("risk_score", ascending=False).drop(columns="geometry")
    top.to_csv(OUTPUTS / "priority_list.csv", index=False)
    plan.to_csv(OUTPUTS / "repair_plan.csv", index=False)

    facilities = clean[clean.asset_type == "fasilitas_kritis"]
    payload = {
        "assets": json.loads(scored.to_json()),
        "zones": json.loads(zone_sum.to_json()),
        "facilities": json.loads(facilities.to_json()),
        "plan_ids": plan["asset_id"].tolist(),
        "budget_idr": budget_idr,
        "bbox": STUDY_BBOX,
    }
    (WEB / "data.js").write_text("window.GEOASSET_DATA = " + json.dumps(payload) + ";", encoding="utf-8")

    report.priority_map(scored, zone_sum)
    report.charts(scored)

    summary = {
        "baris_mentah": int(len(clean) + len(rejected)),
        "baris_bersih": int(len(clean)),
        "baris_ditolak": int(len(rejected)),
        "aset_dinilai": int(len(scored)),
        "prioritas": scored["priority"].value_counts().to_dict(),
        "anggaran_idr": budget_idr,
        "aset_terpilih": int(len(plan)),
        "biaya_terpakai_idr": int(plan["est_cost_idr"].sum()) if len(plan) else 0,
        "risiko_tercakup_pct": round(100 * plan["risk_score"].sum() / scored.loc[scored.risk_score >= DEFAULT_CONFIG.threshold_medium, "risk_score"].sum(), 1) if len(plan) else 0.0,
        "total_kebutuhan_idr": int(scored["est_cost_idr"].sum()),
    }
    (OUTPUTS / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print("[pipeline] ringkasan:\n" + json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=2_000_000_000, help="anggaran perbaikan (Rp)")
    ap.add_argument("--no-regenerate", action="store_true", help="pakai data mentah yang sudah ada")
    a = ap.parse_args()
    main(a.budget, regenerate=not a.no_regenerate)
