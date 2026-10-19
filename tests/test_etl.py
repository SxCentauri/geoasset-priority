import pandas as pd
import pytest

from geoasset.etl import normalize_asset_type, validate


def _row(**kw):
    base = dict(asset_id="LT-1", asset_type="lampu_pju", subtype="led", name="",
                wkt="POINT (102.30 -3.82)", condition=2, install_year=2020,
                last_inspection="2026-01-01", surveyor="Tim-A", notes="")
    base.update(kw)
    return base


@pytest.mark.parametrize("raw,expected", [
    (" Lampu PJU ", "lampu_pju"), ("Gorong-Gorong", "gorong_gorong"),
    ("jalan", "jalan"), (None, ""), (float("nan"), "")])
def test_normalize_asset_type(raw, expected):
    assert normalize_asset_type(raw) == expected


def test_valid_row_is_kept_and_type_normalized():
    clean, bad = validate(pd.DataFrame([_row(asset_type=" Lampu PJU ")]))
    assert len(clean) == 1 and len(bad) == 0
    assert clean.loc[0, "asset_type"] == "lampu_pju"
    assert clean.crs.to_string() == "EPSG:4326"


@pytest.mark.parametrize("override,reason", [
    (dict(wkt=""), "kosong"),
    (dict(wkt="POINT (abc def)"), "tidak valid"),
    (dict(wkt="POINT (-3.82 102.30)"), "luar wilayah"),
    (dict(condition=9), "rentang"),
    (dict(condition=0), "rentang"),
    (dict(install_year=2031), "tahun"),
    (dict(install_year=1890), "tahun"),
    (dict(asset_type="mobil"), "tidak dikenal"),
])
def test_invalid_rows_are_rejected_with_reason(override, reason):
    clean, bad = validate(pd.DataFrame([_row(**override)]))
    assert len(clean) == 0 and len(bad) == 1
    assert reason in bad.loc[0, "reject_reason"]


def test_duplicate_ids_keep_first_only():
    clean, bad = validate(pd.DataFrame([_row(), _row()]))
    assert len(clean) == 1 and bad.loc[0, "reject_reason"] == "asset_id duplikat"


def test_critical_facility_needs_no_condition():
    row = _row(asset_id="FK-1", asset_type="fasilitas_kritis", subtype="sekolah",
               condition=float("nan"), install_year=float("nan"))
    clean, bad = validate(pd.DataFrame([row]))
    assert len(clean) == 1 and len(bad) == 0
