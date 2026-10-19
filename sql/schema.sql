CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS assets_scored (
    asset_id      TEXT PRIMARY KEY,
    asset_type    TEXT NOT NULL,
    subtype       TEXT,
    condition     SMALLINT CHECK (condition BETWEEN 1 AND 5),
    install_year  INTEGER,
    umur          INTEGER,
    f_kondisi     DOUBLE PRECISION,
    f_umur        DOUBLE PRECISION,
    f_kritis      DOUBLE PRECISION,
    risk_score    DOUBLE PRECISION,
    priority      TEXT CHECK (priority IN ('Tinggi','Sedang','Rendah')),
    quantity      DOUBLE PRECISION,
    unit          TEXT,
    est_cost_idr  BIGINT,
    geom          geometry(Geometry, 4326) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_assets_scored_geom ON assets_scored USING GIST (geom);
CREATE INDEX IF NOT EXISTS idx_assets_scored_priority ON assets_scored (priority);
