from __future__ import annotations

import geopandas as gpd
import pandas as pd


def select_within_budget(scored: gpd.GeoDataFrame, budget_idr: int,
                         min_risk: float = 0.0) -> pd.DataFrame:
    cand = scored[(scored.risk_score >= min_risk) & (scored.est_cost_idr > 0)].copy()
    cand["benefit_per_cost"] = cand["risk_score"] / cand["est_cost_idr"]
    cand = cand.sort_values(["benefit_per_cost", "risk_score"], ascending=False)

    spent, picked = 0, []
    for idx, row in cand.iterrows():
        if spent + row.est_cost_idr <= budget_idr:
            picked.append(idx)
            spent += int(row.est_cost_idr)
    plan = cand.loc[picked].drop(columns="geometry", errors="ignore").copy()
    plan["rank"] = range(1, len(plan) + 1)
    plan["cum_cost_idr"] = plan["est_cost_idr"].cumsum()
    return plan
