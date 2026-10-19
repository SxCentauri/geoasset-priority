from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
OUTPUTS = ROOT / "outputs"
WEB = ROOT / "web"
IMAGES = ROOT / "docs" / "images"

CRS_GEO = "EPSG:4326"
CRS_METRIC = "EPSG:32748"

STUDY_BBOX = (102.27, -3.86, 102.34, -3.78)

REFERENCE_YEAR = 2026

ASSET_TYPES = ("jalan", "lampu_pju", "gorong_gorong", "fasilitas_kritis")
MAINTAINABLE_TYPES = ("jalan", "lampu_pju", "gorong_gorong")


@dataclass(frozen=True)
class ScoringConfig:
    w_condition: float = 0.50
    w_age: float = 0.30
    w_criticality: float = 0.20

    design_life: dict = field(default_factory=lambda: {
        "jalan": 15, "lampu_pju": 12, "gorong_gorong": 25})

    type_weight: dict = field(default_factory=lambda: {
        "jalan": 1.0, "lampu_pju": 0.7, "gorong_gorong": 0.85})

    critical_radius_m: float = 500.0
    critical_weights: dict = field(default_factory=lambda: {
        "rumah_sakit": 1.0, "puskesmas": 0.8, "sekolah": 0.6})

    threshold_high: float = 65.0
    threshold_medium: float = 40.0

    cost_per_unit: dict = field(default_factory=lambda: {
        "jalan": 450_000,
        "lampu_pju": 6_500_000,
        "gorong_gorong": 18_000_000})


DEFAULT_CONFIG = ScoringConfig()
