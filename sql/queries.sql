SELECT asset_id, asset_type, risk_score, priority
FROM assets_scored ORDER BY risk_score DESC LIMIT 10;

SELECT l.asset_id, l.risk_score
FROM assets_scored l
JOIN assets_scored r ON r.asset_type = 'jalan' AND r.asset_id = 'RD-0001'
WHERE l.asset_type = 'lampu_pju' AND l.priority = 'Tinggi'
  AND ST_DWithin(l.geom::geography, r.geom::geography, 300);

SELECT asset_type, priority, COUNT(*) AS jumlah, SUM(est_cost_idr) AS total_biaya
FROM assets_scored GROUP BY asset_type, priority ORDER BY asset_type, priority;
